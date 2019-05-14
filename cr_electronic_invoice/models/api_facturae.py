# -*- coding: utf-8 -*-
import datetime
import base64
import pytz

try:
    from lxml import etree
    from lxml.etree import Element, SubElement
except ImportError:
    from xml.etree import ElementTree

def get_time_hacienda():
    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
    date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
    return date_cr


#Utilizada para establecer un limite de caracteres en la cedula del cliente, no mas de 20
#de lo contrario hacienda lo rechaza
def limit(str, limit):
    return (str[:limit - 3] + '...') if len(str) > limit else str


#CONVIERTE UN STRING A BASE 64
def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))


#TOMA UNA CADENA Y ELIMINA LOS CARACTERES AL INICIO Y AL FINAL
def stringStrip(s, start, end):
    return s[start:-end]


#Tomamos el XML y le hacemos el decode de base 64, esto por ahora es solo para probar
#la posible implementacion de la firma en python
def base64decode(string_decode):
    return base64.b64decode(string_decode)


#TOMA UNA CADENA EN BASE64 Y LA DECODIFICA PARA ELIMINAR EL b' Y DEJAR EL STRING CODIFICADO
#DE OTRA MANERA HACIENDA LO RECHAZA
def base64UTF8Decoder(s):
    return s.decode("utf-8")


