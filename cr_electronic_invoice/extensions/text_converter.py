##############################################################################
#
#    Odoo
#    Addons modules by TechMicro Internationcal Company S.A.
#    Copyright (C) 2018-TODAY TechMicro Inc S.A. (<jason.ulloa@techmicrocr.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

_logger = logging.getLogger(__name__)

UNITS = (
    '',
    'UN ',
    'DOS ',
    'TRES ',
    'CUATRO ',
    'CINCO ',
    'SEIS ',
    'SIETE ',
    'OCHO ',
    'NUEVE ',
    'DIEZ ',
    'ONCE ',
    'DOCE ',
    'TRECE ',
    'CATORCE ',
    'QUINCE ',
    'DIECISEIS ',
    'DIECISIETE ',
    'DIECIOCHO ',
    'DIECINUEVE ',
    'VEINTE '
)

TENS = (
    'VENTI',
    'TREINTA ',
    'CUARENTA ',
    'CINCUENTA ',
    'SESENTA ',
    'SETENTA ',
    'OCHENTA ',
    'NOVENTA ',
    'CIEN ',
)

HUNDREDS = (
    'CIENTO ',
    'DOSCIENTOS ',
    'TRESCIENTOS ',
    'CUATROCIENTOS ',
    'QUINIENTOS ',
    'SEISCIENTOS ',
    'SETECIENTOS ',
    'OCHOCIENTOS ',
    'NOVECIENTOS ',
)


def number_to_text_es(number_in, join_dec=' Y ', separator=',', decimal_point='.'):
    converted = ''

    # Check type and convert to str
    if type(number_in) != 'str':
        number = str(number_in)
    else:
        number = number_in

    # Remove the separator from the string
    try:
        number = number.replace(separator, '')
    except ValueError:
        _logger.info(
            "An error occurred while replacing the separator an error may occur.")

    # Get the integer and decimal part of the numbers
    try:
        number_int, number_dec = number.split(decimal_point)
    except ValueError:
        number_int = number
        number_dec = ""
        _logger.info("No decimal part found on the number.")

    number = number_int.zfill(9)
    millions = number[:3]
    thoudsands = number[3:6]
    hundreds = number[6:]

    if millions:
        if millions == '001':
            converted += 'UN MILLON '
        elif int(millions) > 0:
            converted += '%sMILLONES ' % _convert_number(millions)

    if thoudsands:
        if thoudsands == '001':
            converted += 'MIL '
        elif int(thoudsands) > 0:
            converted += '%sMIL ' % _convert_number(thoudsands)

    if hundreds:
        if hundreds == '001':
            converted += 'UN '
        elif int(hundreds) > 0:
            converted += '%s ' % _convert_number(hundreds)

    if number_dec == "":
        number_dec = "00"
    if len(number_dec) < 2:
        number_dec += '0'

    # TODO: Check currency inclusion
    has_decimal = float(number_dec) != 0 and join_dec + \
        number_dec + "/100" or ' EXACTOS'
    converted += has_decimal

    return converted


def _convert_number(n):
    output = ''

    if n == '100':
        output = "CIEN "
    elif n[0] != '0':
        output = HUNDREDS[int(n[0])-1]

    k = int(n[1:])
    if k <= 20:
        output += UNITS[k]
    else:
        if (k > 30) & (n[2] != '0'):
            output += '%sY %s' % (TENS[int(n[1])-2], UNITS[int(n[2])])
        else:
            output += '%s%s' % (TENS[int(n[1])-2], UNITS[int(n[2])])

    return output
