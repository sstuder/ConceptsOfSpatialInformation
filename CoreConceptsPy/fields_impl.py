# -*- coding: utf-8 -*-
"""
TODO: description of module

"""
__author__ = ""
__copyright__ = "Copyright 2014"
__credits__ = ["", "Andrea Ballatore"]
__license__ = ""
__version__ = "0.1"
__maintainer__ = ""
__email__ = ""
__date__ = "December 2014"
__status__ = "Development"

from coreconcepts import AFields
import numpy as np
import gdal
from gdalconst import *

def getGtiffOffset( gtiff, position ):
    """ 
    Convert GeoTiff coordinates to matrix offset. Used for getValue and setValue GeoTiffField functions. 
    @param gtiff - the geotiff
    @param position - the input geocoordinates
    @return - the i,j pair representing position in the image matrix
    """
        
    transform = gtiff.GetGeoTransform()
    #Convert geo-coords to image space
    ulx = transform [0]
    uly = transform [3]
    xQuery = position [0]
    yQuery = position [1]
    pixWidth = transform [1]
    pixHeight = transform [5]
    arrx = int((xQuery - ulx)/pixWidth)
    arry = int((yQuery - uly)/pixHeight)
    return arry, arrx

def squareNeigh(array, size, centerPixel):
    """
    Kernel neighborhood function for focal map algebra. Reutrns square array of specified size.
    @param array - array from which to retrieve the neighborhood kernel
    @param size - size of square in pixels
    @centerPixel - (i,j) corrdinates of center pixel of kernel in the array
    """

    if size > 2:
        ulOffset = int((size - 1) / 2)
    elif size == 2:
        ulOffset = 1
    elif size == 1:
        ulOffset = 0
    rows = centerPixel[0] - ulOffset
    cols = centerPixel[1] - ulOffset
    neighArray = array[rows:rows + size, cols:cols + size]
    return neighArray

class ArrFields(AFields):
    """ Implementation of AField with Python arrays. """
        
    @staticmethod
    def getValue( field, position ):
        x = position[0]
        y = position[1]
        return field[x,y]
    
    @staticmethod
    def setValue( field, position, value ):
        """ @return the position of new value in field """
        x = position[0]
        y = position[1]
        field[x,y] = value
        return field, position, value
     
    @staticmethod
    def domain( field, position, value ):
        """ @return Domains can be described as intervals, rectangles, corner points, convex hulls or boundaries """
        raise NotImplementedError("domain")

"""
TODO: refactor class following OO definitions

class GeoTiffField(CcField):
    def __init__( self, file_path ):
        self.gField = # Load the file
    
    def getValue( self, position ):
        TODO
        self.gField
    
    def local(self, func):
        TODO
        self.gField
        
Tests: 
    gtSolar = GeoTiffField( "data/blabla.gtiff" )
    v =  gtSolar.getValue( 1,2 )
    ... 
"""

class GeoTiffFields(AFields):
    """
    Subclass of Abstract Fields in the GeoTiff format. Based on GDAL.
    
    Map algebra based on (TODO: specify reference. To clarify what we're doing here, it's important to 
    rely on a GIS textbook.
    e.g. Local operations works on individual raster cells, or pixels.
        Focal operations work on cells and their neighbors, whereas global operations work on the entire layer. 
        Finally, zonal operations work on areas of cells that share the same value.
    )
    """
    @staticmethod
    def getValue( gtiff, position ):
        """
        Returns the value of a pixel at an input position
        @param gtiff the GeoTiff
        @param position the coordinate pair in gtiff's coordinate system
        @return the raw value of the pixel at position in gtiff
        """
        offset = getGtiffOffset( gtiff, position )
        #Convert image to array
        array = gtiff.ReadAsArray( offset[1],offset[0], 1,1 )
        return array

    @staticmethod
    #TODO: style: be consistent with "func (" or "func(". "func(" is more common.
    def setValue( gtiff, position, value ):
        """
        Updates the value of a pixel at an input position
        @param gtiff the GeoTiff
        @param position the coordinate pair in GeoTiff's coordinate system
        @param value the new value for pixel at position in GeoTiff
        @return n/a; write to gtiff
        """
        offset = getGtiffOffset( gtiff, position )
        #Convert input value to numpy array
        array = np.array([value], ndmin=2)   #Array has to be 2D in order to write
        band = gtiff.GetRasterBand(1)
        band.WriteArray( array, offset[1],offset[0] )
      
    @staticmethod
    def local(gtiff, newGtiffPath, func):
        """
        Assign a new value to each pixel in gtiff based on func. Return a new GeoTiff at newGtiffPath.
        @param gtiff - the GeoTiff 
        @param newGtiffPath - file path for the new GeoTiff
        @param func - the local function to be applied to each value in GeoTiff
        @return array of new GeoTiff values; write new raster to newGtiffPath
        """
        oldArray = gtiff.ReadAsArray()
        newArray = func(oldArray)
        driver = gtiff.GetDriver()
        newRaster = driver.CreateCopy(newGtiffPath, gtiff)
        outBand = newRaster.GetRasterBand(1)
        outBand.WriteArray(newArray)
        outBand.FlushCache()
        return newArray

    
    @staticmethod
    def focal(gtiff, newGtiffPath, kernFunc,size,func):
        """
        Assign a new value to each pixel in gtiff based on focal map algebra. Return a new GeoTiff at newGtiffPath.
        @param gtiff - the original GeoTiff
        @param newGtiffPath - the filepath of the output GeoTiff
        @param kernFunc - the neighborhood function which returns the kernel array
        @param size - the size of kernel in pixels (this can be expanded to (width, height), or can be built in to kernFunc).
        @return Write to gtiff; return new array
        """
        
        oldArray = gtiff.ReadAsArray()
        newArray = oldArray.copy()
        rows = oldArray.shape[0]
        cols = oldArray.shape[1]
        winOffset = int ((size-1)/2)
        for i in range (winOffset, rows-winOffset):
            for j in range (winOffset, cols-winOffset):
                neighArray = kernFunc(oldArray,size,(i,j))
                newVal = func(neighArray)
                newArray.itemset((i,j), newVal)
        driver = gtiff.GetDriver()
        newRaster = driver.CreateCopy(newGtiffPath, gtiff)
        outBand = newRaster.GetRasterBand(1)
        outBand.WriteArray(newArray)
        outBand.FlushCache()
        return newArray

