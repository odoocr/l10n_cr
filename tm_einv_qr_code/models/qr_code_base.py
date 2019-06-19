# -*- coding: utf-8 -*-
import qrcode
import base64
import io


def generate_qr_code(url):
    qr = qrcode.QRCode(
             version=1,
             error_correction=qrcode.constants.ERROR_CORRECT_L,
             box_size=20,
             border=4,
             )

    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image()
    temp = io.BytesIO()
    img.save(temp, format="PNG")
    qr_img = base64.b64encode(temp.getvalue())
    return qr_img