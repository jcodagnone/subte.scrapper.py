#!/usr/bin/env python
# coding=iso-8859-1
# vim: set ai ts=4 sts=4 textwidth=79 expandtab
#
# Copyright (c) 2008 by Juan F. Codagnone <http://juan.zauber.com.ar> 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; dweither version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

""" 
     scrapea información del subte. arma unas clases con la información de forma
     estandarizada
"""

from BeautifulSoup import BeautifulSoup
import re, urllib2
import time

### utilidad #######################################################
# esto viene de https://svn.leak.com.ar/inmuebles/scrapper.py

class AbstractHttpContentProvider:
    """ clase base para todos los content providers que vayan por http """

    def __init__(self):
        self.headers = {
          'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)',
          'Accept-encoding': 'gzip',
          'Referer':          self.referer,
        }

    def _get(self, url):
        request = urllib2.Request(url)
        for key,value in self.headers.iteritems():
            request.add_header(key,value)
        return urllib2.urlopen(request)

class AbstractMockContentProvider:
    """ clase base para todos los content providers mock  """

    def dumpfile(self, filename):
        f = open(filename)
        s = ''
        for line in f:
            s = s + line
        f.close()
        return s

class SubteContentProvider(AbstractHttpContentProvider):
    mainURL = "http://www.infosubte.com.ar/dekos/Dekos_Subte_2.asp"
    referer = "http://www.subte.com.ar/contenido/home.asp"

    def getContent(self):
        return self._get(self.mainURL)

class MockSubteContentProvider(AbstractMockContentProvider):
    """ provee el contenido de las paginas web...version mock para testeo """
    mainBasePath = 'test/content/Dekos_Subte_2.asp'

    def getContent(self):
        return self.dumpfile(self.mainBasePath)

class LineaSubteStatus:
    def __init__(self, linea, status, periodicidad):
        """
           linea: representa la linea de subte/tren al que representa el estado
                  es una unica letra (A, B, C, ...)
           status: el estado. por ahora es un string (no sabemos los posibles 
                   valores
           periodicidad: cantidad de segundos promedio entre arribos a una 
                         estacion (segundos)
        """
        assert isinstance(periodicidad, int), 'periodicidad debe ser entero'
        assert periodicidad > 0, 'la periodicidad debe ser un entero positivo'
        assert len(linea), 'la linea debe ser un solo caracter'
        assert len(status) > 0, 'debe especificar un estado'

        self.linea = linea
        self.status = status
        self.periodicidad = periodicidad

class StatusSubte:
    def __init__(self, lineas, lastUpdate):
        """
            lineas: arreglo de LineaSubteStatus:
            lastUpdate:  time_t (viene en float) de la fecha que
                         dice el server que fue la ultima actualizacion
        """
        assert isinstance(lastUpdate, float), 'lastUpdate debe ser entero'
        assert lastUpdate > 0, 'lastUpdate debe ser un entero positivo'
        self.lineas = lineas 
        self.lastUpdate = lastUpdate

class SubteScraper:
    rePeriodicidad = re.compile("^Trenes cada (\d+) min. (\d+) seg.$")

    def scrap(self, contentProvider):
        """ retorna un StatusSubte con la informacion en cuestion """
        soup = BeautifulSoup(contentProvider.getContent(),
           convertEntities='html', smartQuotesTo='html')
        l = soup.findAll('tr')
        errorMsg = 'no se encontro los datos esperados'
        assert len(l) == 4, errorMsg
        
        # contiene algo asi como: Actualizado el 16/04/2008 06:26:22 p.m.
        dateStr = ''.join([e for e in l[2].recursiveChildGenerator()
                        if isinstance(e, unicode)]).strip()\
                  .replace('a.m.', 'AM').replace('p.m.', 'PM')[15:]
        # '16/04/2008 06:26:22 P.M.'
        lastUpdate = time.mktime(time.strptime(dateStr, '%d/%m/%Y %I:%M:%S %p'))
        l = l[1].contents[1]
        
        ret = []
        for i in l.contents[1:len(l) - 2]:
            # dice: "Línea E:"
            linea = i.contents[1].renderContents()[-2] 
            # dice algo como: "Servicio Normal"
            status = str(i.contents[2]).strip()
            # dice algo asi como "Trenes cada 3 min. 15 seg."
            periodicidad = str(i.contents[4]).strip()
            m = self.rePeriodicidad.match(periodicidad)
            assert m != None, 'no se pudo parsear la periodicidad de `%s\'' % \
                               periodicidad
            periodicidad = int(m.group(1)) * 60 + int(m.group(2))
            ret.append(LineaSubteStatus(linea, status, periodicidad))
        return StatusSubte(ret, lastUpdate) 

if __name__ == '__main__':
    #contentProvider = MockSubteContentProvider()
    contentProvider = SubteContentProvider()
    status = SubteScraper().scrap(contentProvider)
    print 'Datos de %s' % time.ctime(status.lastUpdate)
    for i in status.lineas:
        print "%s: %s (pasa cada %.2f minutos)" % (i.linea, i.status, 
                                         i.periodicidad / 60 )
