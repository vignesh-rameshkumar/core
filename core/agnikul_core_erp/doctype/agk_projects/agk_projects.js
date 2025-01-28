// Copyright (c) 2025, Agnikul Cosmos Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('AGK_Projects', {
    is_rig: function (frm) {
        if (frm.doc.is_rig) {
            frm.set_value('is_product', 0);
            frm.set_value('is_general', 0);
        }
    },
    is_product: function (frm) {
        if (frm.doc.is_product) {
            frm.set_value('is_rig', 0);
            frm.set_value('is_general', 0);
        }
    },
    is_general: function (frm) {
        if (frm.doc.is_general) {
            frm.set_value('is_rig', 0);
            frm.set_value('is_product', 0);
        }
    },
    validate: function (frm) {
        // Ensure at least one checkbox is selected
        if (!frm.doc.is_rig && !frm.doc.is_product && !frm.doc.is_general) {
            frappe.throw(__('Please select at least one checkbox: Is Rig, Is Product, or Is General.'));
        }

        // Restrict duplicate employee_email
        if (frm.doc.project_members && frm.doc.project_members.length > 0) {
            const emails = [];
            frm.doc.project_members.forEach(member => {
                if (emails.includes(member.employee_email)) {
                    frappe.throw(__('Duplicate employee_email found: {0}', [member.employee_email]));
                }
                emails.push(member.employee_email);
            });
        }
    }
});
