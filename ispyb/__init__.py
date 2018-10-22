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




"""
This package contains the protocols and data for ISPYB
"""
import os
import pyworkflow.em

from pyworkflow.utils import Environ
from .constants import ISPYB_HOME, V1_0_0


_logo = None
_references = ['Delageniere2011']


class Plugin(pyworkflow.em.Plugin):
    _homeVar = ISPYB_HOME

    @classmethod
    def _defineVariables(cls):
        cls._defineEmVar(ISPYB_HOME, 'ispyb-1.0.0')

    @classmethod
    def getEnviron(cls):
        """ Setup the environment variables needed to launch Appion. """
        environ = Environ(os.environ)

        environ.update({
            'PATH': Plugin.getHome(),
        }, position=Environ.BEGIN)

        return environ

    @classmethod
    def isVersionActive(cls):
        return cls.getActiveVersion().startswith(V1_0_0)

    @classmethod
    def defineBinaries(cls, env):
        pass


pyworkflow.em.Domain.registerPlugin(__name__)