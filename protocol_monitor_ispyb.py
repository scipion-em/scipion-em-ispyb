# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es) [1]
# *              Kevin Savage (kevin.savage@diamond.ac.uk) [2]
# *
# * [1] Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# * [2] Diamond Light Source, Ltd
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

from os.path import realpath, join, dirname, exists, basename
import os
from collections import OrderedDict

import pyworkflow.utils as pwutils
import pyworkflow.protocol.params as params
from pyworkflow import VERSION_1_1
from pyworkflow.em import ImageHandler
from pyworkflow.em.protocol import ProtMonitor, Monitor, PrintNotifier
from pyworkflow.em.protocol import ProtImportMovies, ProtAlignMovies, ProtCTFMicrographs
from pyworkflow.gui import getPILImage
from pyworkflow.protocol.constants import STATUS_RUNNING


class ProtMonitorISPyB(ProtMonitor):
    """ Monitor to communicated with ISPyB system at Diamond.
    """
    _label = 'monitor to ISPyB'
    _lastUpdateVersion = VERSION_1_1

    def _defineParams(self, form):
        ProtMonitor._defineParams(self, form)

        group = form.addGroup('Experiment')
        group.addParam('visit', params.StringParam,
                      label="Visit",
                      help="Visit")

        form.addParam('db', params.EnumParam,
                      choices=["production", "devel", "test"],
                      label="Database",
                      help="Select which ISPyB database you want to use.")

    #--------------------------- INSERT steps functions ------------------------
    def _insertAllSteps(self):
        self._insertFunctionStep('monitorStep')

    #--------------------------- STEPS functions -------------------------------
    def monitorStep(self):
        inputProtocols = self.getInputProtocols()

        monitor = MonitorISPyB(self, workingDir=self._getPath(),
                               samplingInterval=self.samplingInterval.get(),
                               monitorTime=100,
                               inputProtocols=inputProtocols,
                               visit=self.visit.get(),
                               dbconf=self.db.get(),
                               project=self.getProject())

        monitor.addNotifier(PrintNotifier())
        monitor.loop()

class MonitorISPyB(Monitor):
    """ This will will be monitoring a CTF estimation protocol.
    It will internally handle a database to store produced
    CTF values.
    """
    def __init__(self, protocol, **kwargs):
        Monitor.__init__(self, **kwargs)
        self.protocol = protocol
        self.allParams = OrderedDict()
        self.numberOfFrames = None
        self.imageGenerator = None
        self.visit = kwargs['visit']
        self.dbconf = kwargs['dbconf']
        self.project = kwargs['project']
        self.inputProtocols = self._sortInputProtocols(kwargs['inputProtocols'])
        self.ispybDb = ISPyBdb(["prod", "dev", "test"][self.dbconf],
                               experimentParams={'visit': self.visit})
    @staticmethod
    def _sortInputProtocols(protList):
        # we need sorted input protocols in order to process objects correctly
        movieProts = []
        alignProts = []
        ctfProts   = []
        for p in protList:
            if isinstance(p, ProtImportMovies):
                movieProts.append(p)
            elif isinstance(p, ProtAlignMovies):
                alignProts.append(p)
            elif isinstance(p, ProtCTFMicrographs):
                ctfProts.append(p)
        sortedProts = movieProts + alignProts + ctfProts
        return sortedProts

    def step(self):
        self.info("MonitorISPyB: only one step")

        prots = [self.getUpdatedProtocol(p) for p in self.inputProtocols]
        finished = [] # store True if protocol not running
        updateIds = [] # Store obj ids that have changes

        for prot in prots:
            self.info("protocol: %s" % prot.getRunName())
            if isinstance(prot, ProtImportMovies) and hasattr(prot, 'outputMovies'):
                self.create_movie_params(prot, updateIds)
            elif isinstance(prot, ProtAlignMovies) and hasattr(prot, 'outputMicrographs'):
                self.update_align_params(prot, updateIds)
            elif isinstance(prot, ProtCTFMicrographs) and hasattr(prot, 'outputCTF'):
                self.update_ctf_params(prot, updateIds)

            finished.append(prot.getStatus() != STATUS_RUNNING)

        for itemId in set(updateIds):
            dcParams = self.ispybDb.get_data_collection_params()
            dcParams.update(self.allParams[itemId])
            ispybId = self.ispybDb.update_data_collection(dcParams)
            self.info("item id: %s" % str(itemId))
            self.info("ispyb id: %s" % str(ispybId))
            # Use -1 as a trick when ISPyB is not really used and id is None
            self.allParams[itemId]['id'] = ispybId or -1

        if all(finished):
            self.info("All finished, closing ISPyBDb connection")
            self.ispybDb.disconnect()

        return all(finished)

    def iter_updated_set(self, objSet):
        objSet.load()
        objSet.loadAllProperties()
        for obj in objSet:
            yield obj
        objSet.close()

    def find_ispyb_path(self, input_file):
        """ Given a visit, find the path where png images should be stored. """
        if pwutils.envVarOn('SCIPIONBOX_ISPYB_ON'):
            p = realpath(join(self.project.path, input_file))
            while p and not p.endswith(self.visit):
                p = dirname(p)
            return join(p, '.ispyb')
        else:
            return self.protocol._getExtraPath()

    def create_movie_params(self, prot, updateIds):

        for movie in self.iter_updated_set(prot.outputMovies):
            movieId = movie.getObjId()
            if movieId in self.allParams:  # this movie has been processed, skip
                continue
            movieFn = movie.getFileName()
            if self.numberOfFrames is None:
                self.numberOfFrames = movie.getNumberOfFrames()
                images_path = self.find_ispyb_path(movieFn)
                self.imageGenerator = ImageGenerator(self.project.path,
                                                     images_path,
                                                     smallThumb=512)

            self.allParams[movieId] = {
                'imgdir': dirname(movieFn),
                'imgprefix': pwutils.removeBaseExt(movieFn),
                'imgsuffix': pwutils.getExt(movieFn),
                'file_template': movieFn,
                'n_images': self.numberOfFrames
             }
            updateIds.append(movieId)

    def update_align_params(self, prot, updateIds):
        for mic in self.iter_updated_set(prot.outputMicrographs):
            micId = mic.getObjId()
            if self.allParams.get(micId, None) is not None:
                if 'comments' in self.allParams[micId]:  # skip if we already have align info
                    continue
                micFn = mic.getFileName()
                renderable_image = self.imageGenerator.generate_image(micFn, micFn)

                self.allParams[micId].update({
                    'comments': 'aligned',
                    'xtal_snapshot1':renderable_image
                })
                print('%d has new align info' % micId)
                updateIds.append(micId)

    def update_ctf_params(self, prot, updateIds):
        for ctf in self.iter_updated_set(prot.outputCTF):
            micId = ctf.getObjId()
            if self.allParams.get(micId, None) is not None:
                if 'min_defocus' in self.allParams[micId]:  # skip if we already have ctf info
                    continue
                micFn = ctf.getMicrograph().getFileName()
                psdName = pwutils.replaceBaseExt(micFn, 'psd.png')
                psdFn = ctf.getPsdFile()
                psdPng = self.imageGenerator.generate_image(psdFn, psdName)
                self.allParams[micId].update({
                'min_defocus': ctf.getDefocusU(),
                'max_defocus': ctf.getDefocusV(),
                'amount_astigmatism': ctf.getDefocusRatio()
                })
                print('%d has new ctf info' % micId)
                updateIds.append(micId)


class ImageGenerator:
    def __init__(self, project_path, images_path,
                 bigThumb=None, smallThumb=None):
        self.project_path = project_path
        self.images_path = images_path
        self.ih = ImageHandler()
        self.img = self.ih.createImage()
        self.bigThumb = bigThumb
        self.smallThumb = smallThumb

    def generate_image(self, input_file, outputName=None):
        output_root = join(self.images_path, basename(outputName))
        output_file = output_root + '.png'

        print "Generating image: ", output_file

        if not exists(output_file):
            from PIL import Image
            self.img.read(join(self.project_path, input_file))
            pimg = getPILImage(self.img)

            pwutils.makeFilePath(output_file)
            if self.bigThumb:
                pimg.save(output_file, "PNG")

            if self.smallThumb:
                pimg.thumbnail((self.smallThumb, self.smallThumb), Image.ANTIALIAS)
                pimg.save(output_root + 't.png', "PNG")

        return output_file


def _loadMeanShifts(self, movie):
    alignMd = md.MetaData(self._getOutputShifts(movie))
    meanX = alignMd.getColumnValues(md.MDL_OPTICALFLOW_MEANX)
    meanY = alignMd.getColumnValues(md.MDL_OPTICALFLOW_MEANY)

    return meanX, meanY


def _saveAlignmentPlots(self, movie):
    """ Compute alignment shifts plot and save to file as a png image. """
    meanX, meanY = self._loadMeanShifts(movie)
    plotter = createAlignmentPlot(meanX, meanY)
    plotter.savefig(self._getPlotCart(movie))


def createAlignmentPlot(meanX, meanY):
    """ Create a plotter with the cumulative shift per frame. """
    sumMeanX = []
    sumMeanY = []
    figureSize = (8, 6)
    plotter = Plotter(*figureSize)
    figure = plotter.getFigure()

    preX = 0.0
    preY = 0.0
    sumMeanX.append(0.0)
    sumMeanY.append(0.0)
    ax = figure.add_subplot(111)
    ax.grid()
    ax.set_title('Cartesian representation')
    ax.set_xlabel('Drift x (pixels)')
    ax.set_ylabel('Drift y (pixels)')
    ax.plot(0, 0, 'yo-')
    i = 1
    for x, y in izip(meanX, meanY):
        preX += x
        preY += y
        sumMeanX.append(preX)
        sumMeanY.append(preY)
        #ax.plot(preX, preY, 'yo-')
        ax.text(preX-0.02, preY+0.02, str(i))
        i += 1

    ax.plot(sumMeanX, sumMeanY, color='b')
    ax.plot(sumMeanX, sumMeanY, 'yo')

    plotter.tightLayout()

    return plotter


class ISPyBdb:
    """ This is a Facade to provide access to the ispyb_api to store movies."""
    def __init__(self, db, experimentParams):
        self.experimentParams = experimentParams

        from ispyb.dbconnection import dbconnection
        from ispyb.core import core
        from ispyb.mxacquisition import mxacquisition
        self.dbconnection = dbconnection
        self.core = core
        self.mxacquisition = mxacquisition

        self._loadCursor(db)
        self._create_group()

    def _loadCursor(self, db):
        # db should be one of: 'prod', 'dev' or 'test'
        # let's try to connect to db and get a cursor
        if self.dbconnection:
            self.cursor = self.dbconnection.connect(db)

    def _create_group(self):
        self.visit_id = self.core.retrieve_visit_id(self.cursor, self.experimentParams['visit'])
        params = self.mxacquisition.get_data_collection_group_params()
        params['parentid'] = self.visit_id
        self.group_id = self.mxacquisition.insert_data_collection_group(self.cursor, params.values())

    def get_data_collection_params(self):
        params = self.mxacquisition.get_data_collection_params()
        params['parentid'] = self.group_id
        params['visitid'] = self.visit_id
        return params

    def update_data_collection(self, params):
        return self.mxacquisition.insert_data_collection(self.cursor, params.values())

    def disconnect(self):
        if self.dbconnection:
            self.dbconnection.disconnect()
