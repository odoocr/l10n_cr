.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================
Base FE Costa Rica
==================

This is the base module for the implementation of the `Costa Rica Electronic Invoice <https://www.hacienda.go.cr/ATV/ComprobanteElectronico/frmAnexosyEstructuras.aspx>`_ Implementation.

This module contains methods to generate and parse XML files. This module doesn't do anything useful by itself, but it is used by these other modules:

* *account_invoice_import_fe_cr* that imports XML electronic invoices and tries to attach XML response from Hacienda and PDF representation of the invoice,

Configuration
=============

No configuration is needed.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/CRLibre/fe-hacienda-cr-odoo>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>

* `Delfix S.A. <https://www.antiun.com>`_:
  * Mario Arias <support@cysfuturo.com>

* `AKUREY S.A. <https://www.akurey.com>`_:
  * Carlos Wong <cwong@akurey.com>
  * Sergio Hidalgo <shidalgo@akurey.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by Odoo Costa Rica Community at https://github.com/CRLibre/fe-hacienda-cr-odoo.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

AKUREY, is a private company whose mission is to support and innovate thru digital technology.
AKUREY collaborate in the development of Odoo features and promote its widespread use.

To contribute to this module, please visit https://github.com/CRLibre/fe-hacienda-cr-odoo and the Telegram group https://t.me/CRLibreOdoo.
