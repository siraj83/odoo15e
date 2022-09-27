# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    insz_or_bis_number = fields.Char("INSZ or BIS number")
    clocked_session_ids = fields.Many2many(
        'pos.session',
        'employees_session_clocking_info',
        string='Users Clocked In',
        help='This is a technical field used for tracking the status of the session for each employees.',
    )

    @api.constrains('insz_or_bis_number')
    def _check_insz_or_bis_number(self):
        for emp in self:
            if emp.insz_or_bis_number and (len(emp.insz_or_bis_number) != 11 or not emp.insz_or_bis_number.isdigit()):
                raise ValidationError(_("The INSZ or BIS number has to consist of 11 numerical digits."))


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    insz_or_bis_number = fields.Char("INSZ or BIS number", readonly=True)
