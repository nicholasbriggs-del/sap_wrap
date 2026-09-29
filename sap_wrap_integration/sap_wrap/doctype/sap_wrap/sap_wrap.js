frappe.sap_wrap = {
    get_fields_options_from_meta(meta) {
        const opts = [];
        if (!meta) return opts;
        (meta.fields || []).forEach((d) => {
            if (
                frappe.model.no_value_type.includes(d.fieldtype) ||
                frappe.model.table_fields.includes(d.fieldtype)
            ) {
                return;
            }
            opts.push({ label: `${__(d.label, null, d.parent)} (${__(d.fieldtype)})`, value: d.fieldname });
        });
        for (let field of frappe.model.std_fields) {
            if (field.fieldname == "name") {
                opts.unshift({ label: __("Name (Doc Name)"), value: "name" });
            } else {
                opts.push({ label: `${__(field.label, null, field.parent)} (${__(field.fieldtype)})`, value: field.fieldname });
            }
        }
        return opts;
    },
    fetch_workflow_states(frm) {
        if (!frm.doc.target_doctype) {
            frm.workflow_states = [];
            frappe.sap_wrap.apply_workflow_state_query(frm);
            return Promise.resolve([]);
        }
        frm.workflow_states = frm.workflow_states || [];
        return frappe
            .call({
                method: "sap_wrap_integration.sap_wrap.doctype.sap_wrap.sap_wrap.get_workflow_states",
                args: { document_type: frm.doc.target_doctype },
                freeze: false,
            })
            .then((r) => {
                frm.workflow_states = r.message || [];
                frappe.sap_wrap.apply_workflow_state_query(frm);
                return frm.workflow_states;
            })
            .catch(() => {
                frm.workflow_states = [];
                frappe.sap_wrap.apply_workflow_state_query(frm);
                return [];
            });
    },
    apply_workflow_state_query(frm) {
        const states = frm.workflow_states || [];
        frm.set_query("workflow_state", "workflow_state_mappings", () => {
            if (!states.length) {
                return { filters: { name: ["in", []] } };
            }
            return { filters: { name: ["in", states] } };
        });
        frm.refresh_field("workflow_state_mappings");
    },
    open_insert_key_field_dialog(frm) {
        if (!frm.doc.target_doctype) {
            frappe.msgprint({ message: __("Select Target DocType first."), indicator: "orange" });
            return;
        }
        frappe.model.with_doctype(frm.doc.target_doctype, () => {
            const meta = frappe.get_doc("DocType", frm.doc.target_doctype);
            const fields = this.get_fields_options_from_meta(meta);
            const d = new frappe.ui.Dialog({
                title: __("Insert Key from Doc Field"),
                fields: [
                    { fieldname: "key", fieldtype: "Data", label: __("JSON Key"), reqd: 1 },
                    { fieldname: "fieldname", fieldtype: "Select", label: __("Doc Field"), options: [""] .concat(fields), reqd: 1 },
                ],
                primary_action_label: __("Insert"),
                primary_action: (values) => {
                    try {
                        const txt = frm.doc.request_body_template || "{}";
                        const obj = JSON.parse(txt);
                        obj[values.key] = `{{ doc.${values.fieldname} }}`;
                        frm.set_value("request_body_template", JSON.stringify(obj, null, 2));
                        d.hide();
                    } catch (e) {
                        frappe.msgprint({ message: __("Request Body is not valid JSON. Fix it or clear to {} first."), indicator: "red" });
                    }
                },
            });
            d.show();
        });
    },
    open_insert_base64_dialog(frm) {
        if (!frm.doc.target_doctype) {
            frappe.msgprint({ message: __("Select Target DocType first."), indicator: "orange" });
            return;
        }
        frappe.model.with_doctype(frm.doc.target_doctype, () => {
            const meta = frappe.get_doc("DocType", frm.doc.target_doctype);
            const file_fields = (meta.fields || []).filter(f => ["Attach", "Attach Image"].includes(f.fieldtype))
                .map(f => ({ label: `${__(f.label)} (${f.fieldtype})`, value: f.fieldname }));
            const d = new frappe.ui.Dialog({
                title: __("Insert Base64 Attachment"),
                fields: [
                    { fieldname: "key", fieldtype: "Data", label: __("JSON Key"), reqd: 1 },
                    { fieldname: "fieldname", fieldtype: "Select", label: __("Attachment Field"), options: [""] .concat(file_fields), reqd: 1 },
                ],
                primary_action_label: __("Insert"),
                primary_action: (values) => {
                    try {
                        const txt = frm.doc.request_body_template || "{}";
                        const obj = JSON.parse(txt);
                        obj[values.key] = `{{ file_b64(doc.${values.fieldname}) }}`;
                        frm.set_value("request_body_template", JSON.stringify(obj, null, 2));
                        d.hide();
                    } catch(e) {
                        frappe.msgprint({ message: __("Request Body is not valid JSON. Fix it or clear to {} first."), indicator: "red" });
                    }
                },
            });
            d.show();
        });
    },
    test_execute(frm) {
        if (!frm.doc.preview_document) {
            frappe.msgprint({ message: __("Select a Preview Document first."), indicator: "orange" });
            return;
        }
        frappe.call({
            method: "sap_wrap_integration.sap_wrap.doctype.sap_wrap.sap_wrap.test_execute",
            args: { name: frm.doc.name, docname: frm.doc.preview_document },
        }).then(r => {
            const res = r.message || {};
            const workflowState = res.applied_workflow_state ? __(res.applied_workflow_state) : __("None");
            const dlg = new frappe.ui.Dialog({
                title: __("Test Execute Result"),
                fields: [
                    { fieldname: "status", fieldtype: "Data", label: __("Status"), read_only: 1, default: res.status },
                    { fieldname: "workflow", fieldtype: "Data", label: __("Workflow State"), read_only: 1, default: workflowState },
                    { fieldname: "response", fieldtype: "Code", label: __("Response"), read_only: 1, default: (res.response_text || JSON.stringify(res.response_json || {}, null, 2)) },
                ],
                primary_action_label: __("Close"),
                primary_action: () => dlg.hide(),
            });
            dlg.show();
        }).catch(e => {
            frappe.msgprint({ message: __("Execution failed. Check server logs."), indicator: "red" });
        });
    },
    open_insert_array_item_dialog(frm) {
        if (!frm.doc.target_doctype) {
            frappe.msgprint({ message: __("Select Target DocType first."), indicator: "orange" });
            return;
        }
        frappe.model.with_doctype(frm.doc.target_doctype, () => {
            const meta = frappe.get_doc("DocType", frm.doc.target_doctype);
            const doc_fields = frappe.sap_wrap.get_fields_options_from_meta(meta);
            const attach_fields = (meta.fields || []).filter(f => ["Attach", "Attach Image"].includes(f.fieldtype))
                .map(f => ({ label: `${__(f.label)} (${f.fieldtype})`, value: f.fieldname }));

            const build_fields = (count) => {
                const fields = [
                    { fieldname: "array_key", fieldtype: "Data", label: __("Array Key"), reqd: 1 },
                    { fieldname: "repeat_key", fieldtype: "Data", label: __("Repeat Key (optional)") },
                    { fieldname: "repeat_values", fieldtype: "Small Text", label: __("Repeat Values (comma/newline separated)") },
                    { fieldname: "sb_map", fieldtype: "Section Break", label: __("Mappings") },
                ];
                for (let i = 1; i <= count; i++) {
                    fields.push({ fieldname: `k${i}`, fieldtype: "Data", label: __("Key ") + i });
                    fields.push({ fieldname: `vt${i}`, fieldtype: "Select", label: __("Value Type ") + i, options: ["Constant", "Doc Field", "Attach Base64"], default: "Doc Field" });
                    fields.push({ fieldname: `v${i}`, fieldtype: "Data", label: __("Value ") + i });
                    fields.push({ fieldname: `f${i}`, fieldtype: "Select", label: __("Field ") + i, options: [""] .concat(doc_fields) });
                    fields.push({ fieldname: `a${i}`, fieldtype: "Select", label: __("Attach Field ") + i, options: [""] .concat(attach_fields) });
                    if (i < count) fields.push({ fieldname: `br${i}`, fieldtype: "Column Break" });
                }
                return fields;
            };

            const open_dialog = (count, preset = {}) => {
                const d = new frappe.ui.Dialog({
                    title: __("Insert Array Item(s)"),
                    fields: build_fields(count),
                    primary_action_label: __("Insert"),
                    primary_action: (values) => {
                        try {
                            const build_obj = (override = {}) => {
                                const obj = {};
                                for (let i = 1; i <= count; i++) {
                                    const k = values[`k${i}`];
                                    const vt = values[`vt${i}`];
                                    const v = values[`v${i}`];
                                    const f = values[`f${i}`];
                                    const a = values[`a${i}`];
                                    if (!k) continue;
                                    if (override.hasOwnProperty(k)) { obj[k] = override[k]; continue; }
                                    if (vt === "Constant") { if (v !== undefined && v !== "") obj[k] = v; }
                                    else if (vt === "Doc Field") { if (f) obj[k] = `{{ doc.${f} }}`; }
                                    else if (vt === "Attach Base64") { if (a) obj[k] = `{{ file_b64(doc.${a}) }}`; }
                                }
                                return obj;
                            };

                            const txt = frm.doc.request_body_template || "{}";
                            const root = JSON.parse(txt);
                            const key = values.array_key;
                            if (!root[key]) root[key] = [];
                            if (!Array.isArray(root[key])) root[key] = [];

                            const rkey = (values.repeat_key || "").trim();
                            const rvals = (values.repeat_values || "").split(/\n|,/).map(s => s.trim()).filter(Boolean);
                            if (rkey && rvals.length) {
                                for (const rv of rvals) {
                                    const obj = build_obj({ [rkey]: rv });
                                    if (Object.keys(obj).length) root[key].push(obj);
                                }
                            } else {
                                const obj = build_obj();
                                if (Object.keys(obj).length) root[key].push(obj);
                            }
                            frm.set_value("request_body_template", JSON.stringify(root, null, 2));
                            d.hide();
                        } catch (e) {
                            console.error(e);
                            frappe.msgprint({ message: __("Request Body is not valid JSON. Fix it or clear to {} first."), indicator: "red" });
                        }
                    },
                    secondary_action_label: __("Add Mapping"),
                    secondary_action: () => {
                        const current = d.get_values() || {};
                        d.hide();
                        open_dialog(count + 1, current);
                    },
                });
                if (preset && Object.keys(preset).length) {
                    d.set_values(preset);
                }
                d.show();
            };

            open_dialog(1);
        });
    },
    open_insert_header_field_dialog(frm) {
        const rows = (frm.doc.sap_wrap_headers || []).map(r => ({ label: `${r.key}`, value: r.key }));
        if (!rows.length) {
            frappe.msgprint({ message: __("Add at least one header row first."), indicator: "orange" });
            return;
        }
        if (!frm.doc.target_doctype) {
            frappe.msgprint({ message: __("Select Target DocType first."), indicator: "orange" });
            return;
        }
        frappe.model.with_doctype(frm.doc.target_doctype, () => {
            const meta = frappe.get_doc("DocType", frm.doc.target_doctype);
            const fields = frappe.sap_wrap.get_fields_options_from_meta(meta);
            const d = new frappe.ui.Dialog({
                title: __("Insert Header Field"),
                fields: [
                    { fieldname: "hkey", fieldtype: "Select", label: __("Header Key"), options: [""] .concat(rows), reqd: 1 },
                    { fieldname: "f", fieldtype: "Select", label: __("Doc Field"), options: [""] .concat(fields), reqd: 1 },
                    { fieldname: "append", fieldtype: "Check", label: __("Append (otherwise replace)"), default: 1 },
                ],
                primary_action_label: __("Apply"),
                primary_action: (values) => {
                    const token = `{{ doc.${values.f} }}`;
                    const row = (frm.doc.sap_wrap_headers || []).find(r => r.key === values.hkey);
                    if (!row) return d.hide();
                    const current = row.value || "";
                    const next = values.append ? (current ? current + " " + token : token) : token;
                    frappe.model.set_value(row.doctype, row.name, "value", next);
                    d.hide();
                },
            });
            d.show();
        });
    },
    toggle_endpoint_url_read_only(frm) {
        const isDynamic = cint(frm.doc.is_dynamic_url || 0);
        frm.set_df_property("endpoint_url", "read_only", !isDynamic);
        frm.refresh_field("endpoint_url");
    },
};

frappe.ui.form.on("SAP Wrap", {
    refresh: (frm) => {
        frm.set_query(
            "background_jobs_queue",
            "frappe.integrations.doctype.webhook.webhook.get_all_queues"
        );
        // Inline editor toolbar for Request Body JSON
        frappe.sap_wrap.render_body_editor_toolbar(frm);
        frm.add_custom_button(__("Test Execute"), () => frappe.sap_wrap.test_execute(frm), "Preview");
        frappe.sap_wrap.toggle_endpoint_url_read_only(frm);

        const headersGrid = frm.fields_dict.sap_wrap_headers && frm.fields_dict.sap_wrap_headers.grid;
        if (headersGrid && !headersGrid._sap_header_button_added) {
            headersGrid.add_custom_button(__("Insert Header Field"), () => frappe.sap_wrap.open_insert_header_field_dialog(frm));
            headersGrid._sap_header_button_added = true;
        }

        const mappingGrid = frm.fields_dict.response_mappings && frm.fields_dict.response_mappings.grid;
        if (mappingGrid && !mappingGrid._sap_mapping_buttons_added) {
            mappingGrid.add_custom_button(__("Edit Mapping"), () => {
                const selected = mappingGrid.get_selected();
                const name = Array.isArray(selected) && selected.length ? selected[0] : null;
                frappe.sap_wrap.open_edit_response_mapping_dialog(frm, name);
            });
            mappingGrid.add_custom_button(__("Map From Response"), () => frappe.sap_wrap.open_map_from_response_dialog(frm));
            mappingGrid._sap_mapping_buttons_added = true;
        }

        frappe.sap_wrap.fetch_workflow_states(frm);
    },
    target_doctype: (frm) => {
        frappe.sap_wrap.toggle_endpoint_url_read_only(frm);
        frappe.sap_wrap.fetch_workflow_states(frm);
    },
    api_endpoint: (frm) => {
        if (!frm.doc.api_endpoint) return;
        frappe.call({
            method: "sap_wrap_integration.sap_wrap.doctype.sap_wrap.sap_wrap.load_endpoint_defaults",
            args: { api_endpoint: frm.doc.api_endpoint },
        }).then(r => {
            const d = r.message || {};
            if (d.request_method) frm.set_value("request_method", d.request_method);
            if (d.endpoint_url) frm.set_value("endpoint_url", d.endpoint_url);
            if (typeof d.request_body_template === "string") {
                frm.set_value("request_body_template", d.request_body_template);
            }
            if (Array.isArray(d.headers)) {
                frm.clear_table("sap_wrap_headers");
                d.headers.forEach(h => {
                    const row = frm.add_child("sap_wrap_headers");
                    row.key = h.key;
                    row.value = h.value;
                });
                frm.refresh_field("sap_wrap_headers");
            }
            frappe.sap_wrap.toggle_endpoint_url_read_only(frm);
        });
    },
    preview_document: (frm) => {
        frappe.call({
            method: "generate_preview",
            doc: frm.doc,
            callback: () => {
                frm.refresh_field("meets_condition");
                frm.refresh_field("preview_request_body");
                frm.refresh_field("workflow_state_mappings");
            },
        });
    },
    is_dynamic_url: (frm) => {
        frappe.sap_wrap.toggle_endpoint_url_read_only(frm);
    },
});

// Inline toolbar below the JSON editor (request_body_template)
frappe.sap_wrap.render_body_editor_toolbar = function(frm) {
    const field = frm.fields_dict.request_body_template;
    if (!field || !field.$wrapper) return;
    // Avoid duplicates
    if (field.$wrapper.find('.sap-wrap-body-toolbar').length) return;

    const $bar = $(`
        <div class="sap-wrap-body-toolbar" style="margin-top: 6px; display:flex; gap:8px;">
            <button class="btn btn-xs btn-default" type="button">${__("Edit JSON Value")}</button>
            <button class="btn btn-xs btn-default" type="button">${__("Add JSON Key")}</button>
            <button class="btn btn-xs btn-default" type="button">${__("Insert Array Item")}</button>
        </div>
    `);
    field.$wrapper.append($bar);

    const [$editBtn, $addBtn, , $arrayBtn] = $bar.find('button').toArray();

    $editBtn.addEventListener('click', () => frappe.sap_wrap.open_edit_json_value_dialog(frm));
    $addBtn.addEventListener('click', () => frappe.sap_wrap.open_insert_key_field_dialog(frm));
    $arrayBtn.addEventListener('click', () => frappe.sap_wrap.open_insert_array_item_dialog(frm));
};

// Open dialog to edit an existing key's value in JSON
frappe.sap_wrap.open_edit_json_value_dialog = function(frm) {
    const template = frm.doc.request_body_template || '{}';
    let obj;
    let hasDynamicTail = false;
    let dynamicTail = '';
    let dynamicHadComma = false;
    try {
        obj = JSON.parse(template);
    } catch (err) {
        const splitIndex = template.indexOf('{%');
        if (splitIndex !== -1) {
            const staticPart = template.slice(0, splitIndex);
            dynamicTail = template.slice(splitIndex);
            dynamicHadComma = /,\s*$/.test(staticPart);
            let sanitized = dynamicHadComma ? staticPart.replace(/,\s*$/, '') : staticPart;
            sanitized = sanitized.trimEnd();
            if (!sanitized.endsWith('}')) {
                sanitized = sanitized + '\n}';
            }
            try {
                obj = JSON.parse(sanitized);
                hasDynamicTail = true;
            } catch (inner) {
                if (/{[{%]/.test(template)) {
                    frappe.sap_wrap.open_raw_template_dialog(frm, template, inner);
                } else {
                    frappe.msgprint({ message: __("Request Body is not valid JSON."), indicator: "red" });
                }
                return;
            }
        } else {
            if (/{[{%]/.test(template)) {
                frappe.sap_wrap.open_raw_template_dialog(frm, template, err);
            } else {
                frappe.msgprint({ message: __("Request Body is not valid JSON."), indicator: "red" });
            }
            return;
        }
    }

    // Flatten object to dot paths of leaf values
    const paths = [];
    const walk = (cur, prefix) => {
        if (cur !== null && typeof cur === 'object') {
            if (Array.isArray(cur)) {
                cur.forEach((v, i) => walk(v, prefix ? `${prefix}.${i}` : `${i}`));
            } else {
                Object.keys(cur).forEach(k => walk(cur[k], prefix ? `${prefix}.${k}` : k));
            }
        } else {
            paths.push(prefix);
        }
    };
    walk(obj, '');
    const path_options = paths.map(p => ({ label: p, value: p }));

    const prepare_field_options = (cb) => {
        if (!frm.doc.target_doctype) return cb([],[ ]);
        frappe.model.with_doctype(frm.doc.target_doctype, () => {
            const meta = frappe.get_doc('DocType', frm.doc.target_doctype);
            const doc_fields = frappe.sap_wrap.get_fields_options_from_meta(meta);
            const attach_fields = (meta.fields || []).filter(f => ['Attach','Attach Image'].includes(f.fieldtype))
                .map(f => ({ label: `${__(f.label)} (${f.fieldtype})`, value: f.fieldname }));
            cb(doc_fields, attach_fields);
        });
    };

    prepare_field_options((doc_fields, attach_fields) => {
        const utilityOptions = [
            { label: __("Random Digits"), value: 'random_digits' },
            { label: __("Financial Year Start"), value: 'fiscal_year_start' },
            { label: __("Financial Year End"), value: 'fiscal_year_end' },
        ];

        const d = new frappe.ui.Dialog({
            title: __("Edit JSON Value"),
            fields: [
                { fieldname: 'target_path', fieldtype: 'Select', label: __("Path"), options: [''].concat(path_options), reqd: 1 },
                { fieldname: 'vt', fieldtype: 'Select', label: __("Value Type"), options: ['Constant','Doc Field','Attach Base64','Utility'], default: 'Doc Field', reqd: 1 },
                { fieldname: 'v', fieldtype: 'Data', label: __("Value (for Constant)") },
                { fieldname: 'f', fieldtype: 'Select', label: __("Doc Field"), options: [''].concat(doc_fields) },
                { fieldname: 'a', fieldtype: 'Select', label: __("Attach Field"), options: [''].concat(attach_fields) },
                { fieldname: 'utility', fieldtype: 'Select', label: __("Utility"), options: [''].concat(utilityOptions), default: 'random_digits' },
                { fieldname: 'digits', fieldtype: 'Int', label: __("Digit Count"), description: __("1 – 18"), default: 6 },
            ],
            primary_action_label: __("Apply"),
            primary_action: (values) => {
                try {
                    const set_by_path = (root, path, value) => {
                        const parts = path.split('.');
                        let cur = root;
                        for (let i = 0; i < parts.length - 1; i++) {
                            const k = parts[i];
                            const idx = String(parseInt(k)) === k ? parseInt(k) : null;
                            if (idx !== null) {
                                cur = cur[idx];
                            } else {
                                cur = cur[k];
                            }
                        }
                        const last = parts[parts.length - 1];
                        const lastIdx = String(parseInt(last)) === last ? parseInt(last) : null;
                        if (lastIdx !== null) {
                            cur[lastIdx] = value;
                        } else {
                            cur[last] = value;
                        }
                    };

                    let newVal;
                    if (values.vt === 'Constant') {
                        newVal = values.v;
                    } else if (values.vt === 'Doc Field') {
                        if (!values.f) {
                            frappe.msgprint({ message: __("Select a Doc Field."), indicator: 'red' });
                            return;
                        }
                        newVal = `{{ doc.${values.f} }}`;
                    } else if (values.vt === 'Attach Base64') {
                        if (!values.a) {
                            frappe.msgprint({ message: __("Select an attachment field."), indicator: 'red' });
                            return;
                        }
                        newVal = `{{ file_b64(doc.${values.a}) }}`;
                    } else if (values.vt === 'Utility') {
                        const util = values.utility;
                        if (util === 'random_digits') {
                            const rawDigits = parseInt(values.digits, 10);
                            const digits = Number.isFinite(rawDigits) ? Math.min(Math.max(rawDigits, 1), 18) : 6;
                            newVal = `{{ random_digits(${digits}) }}`;
                        } else if (util === 'fiscal_year_start' || util === 'fiscal_year_end') {
                            const fnName = util;
                            newVal = `{{ ${fnName}() }}`;
                        } else {
                            frappe.msgprint({ message: __("Select a utility."), indicator: 'red' });
                            return;
                        }
                    }

                    set_by_path(obj, values.target_path, newVal);
                    const updated = frappe.sap_wrap.compose_template_from_json(obj, {
                        dynamic_tail: hasDynamicTail ? dynamicTail : '',
                        had_trailing_comma: hasDynamicTail ? dynamicHadComma : false,
                    });
                    frm.set_value('request_body_template', updated);
                    d.hide();
                } catch (e) {
                    frappe.msgprint({ message: __("Failed to update JSON value."), indicator: 'red' });
                }
            },
        });
        const toggleDisplays = () => {
            const vt = d.get_value('vt');
            d.toggle_display('v', vt === 'Constant');
            d.toggle_display('f', vt === 'Doc Field');
            d.toggle_display('a', vt === 'Attach Base64');
            const showUtility = vt === 'Utility';
            d.toggle_display('utility', showUtility);
            if (showUtility && !d.get_value('utility')) {
                d.set_value('utility', 'random_digits');
            }
            const util = d.get_value('utility');
            d.toggle_display('digits', showUtility && util === 'random_digits');
            if (!showUtility) {
                d.set_value('utility', '');
                d.set_value('digits', 6);
            }
        };

        const vtField = d.fields_dict.vt;
        const utilField = d.fields_dict.utility;
        vtField.df.onchange = toggleDisplays;
        utilField.df.onchange = toggleDisplays;

        d.show();
        toggleDisplays();
    });
};

frappe.sap_wrap.open_raw_template_dialog = function(frm, template, error) {
    const dlg = new frappe.ui.Dialog({
        title: __("Edit Request Body Template"),
        fields: [
            {
                fieldname: 'template',
                fieldtype: 'Code',
                options: 'JSON',
                default: template || '{}',
                description: __("Template contains Jinja control statements; edit the raw text directly."),
            },
        ],
        primary_action_label: __("Save"),
        primary_action(values) {
            dlg.disable_primary_action();
            frm.set_value('request_body_template', values.template || '');
            dlg.hide();
            frappe.show_alert({ message: __("Request body template updated."), indicator: 'green' });
        },
        secondary_action_label: __("Cancel"),
        secondary_action() {
            dlg.hide();
        },
    });

    if (error) {
        dlg.set_df_property('template', 'description', __("Jinja detected; raw editing enabled. ({0})", [error.message || error]));
    }

    dlg.show();
};

frappe.sap_wrap.compose_template_from_json = function(obj, opts = {}) {
    const dynamicTail = opts.dynamic_tail || '';
    const hadComma = opts.had_trailing_comma || false;
    const jsonStr = JSON.stringify(obj, null, 2);
    if (!dynamicTail) {
        return jsonStr;
    }

    let prefix = jsonStr.trimEnd();
    prefix = prefix.replace(/\s*}\s*$/, '');

    let tail = dynamicTail;
    if (!tail.startsWith('\n')) {
        tail = '\n' + tail;
    }

    if (hadComma) {
        return `${prefix},${tail}`;
    }
    return `${prefix}${tail}`;
};

// Build response → doc mapping from a sample (endpoint sample or last response)
frappe.sap_wrap.open_map_from_response_dialog = function(frm) {
    if (!frm.doc.target_doctype) {
        frappe.msgprint({ message: __("Select Target DocType first."), indicator: "orange" });
        return;
    }
    const docname = frm.doc.preview_document || frm.doc.name;
    frappe.call({
        method: "sap_wrap_integration.sap_wrap.doctype.sap_wrap.sap_wrap.get_response_samples",
        args: { name: frm.doc.name, docname },
    }).then(r => {
        const endpoint_sample = r.message && r.message.endpoint_sample;
        const last_response = r.message && r.message.last_response;
        let source = endpoint_sample || (last_response ? JSON.stringify(last_response) : "{}");
        if (!source) source = "{}";
        let obj;
        try { obj = JSON.parse(source); } catch (e) { obj = {}; }

        // flatten
        const entries = [];
        const walk = (cur, prefix) => {
            if (cur !== null && typeof cur === 'object') {
                if (Array.isArray(cur)) {
                    cur.forEach((v, i) => walk(v, prefix ? `${prefix}.${i}` : `${i}`));
                } else {
                    Object.keys(cur).forEach(k => walk(cur[k], prefix ? `${prefix}.${k}` : k));
                }
            } else {
                entries.push({ path: prefix, value: cur });
            }
        };
        walk(obj, '');

        // Load target fields for mapping
        frappe.model.with_doctype(frm.doc.target_doctype, () => {
            const meta = frappe.get_doc('DocType', frm.doc.target_doctype);
            const fields = (meta.fields || [])
                .filter(df => !frappe.model.no_value_type.includes(df.fieldtype) && !frappe.model.table_fields.includes(df.fieldtype))
                .map(df => ({ label: `${__(df.label)} (${df.fieldtype})`, value: df.fieldname }));
            fields.unshift({ label: __("Name (Doc Name)"), value: "name" });

            const path_opts = entries.map(e => ({ label: `${e.path}`, value: e.path }));
            const d = new frappe.ui.Dialog({
                title: __("Map From Response"),
                fields: [
                    { fieldname: 'path', fieldtype: 'Select', label: __("Response Path"), options: [''].concat(path_opts), reqd: 1 },
                    { fieldname: 'field', fieldtype: 'Select', label: __("Target Field"), options: [''].concat(fields), reqd: 1 },
                    { fieldname: 'transform', fieldtype: 'Select', label: __("Transform"), options: ['None','To Int','To Float','To String','Length','Digits Only','Regex'], default: 'None' },
                    { fieldname: 'regex_pattern', fieldtype: 'Data', label: __("Regex Pattern (for Regex)") },
                    { fieldname: 'default_value', fieldtype: 'Data', label: __("Default Value") },
                    { fieldname: 'required', fieldtype: 'Check', label: __("Required") },
                ],
                primary_action_label: __("Add Mapping"),
                primary_action: (values) => {
                    const row = frm.add_child('response_mappings');
                    row.response_path = values.path;
                    row.target_field = values.field;
                    row.transform = values.transform;
                    row.regex_pattern = values.regex_pattern;
                    row.default_value = values.default_value;
                    row.required = values.required ? 1 : 0;
                    frm.refresh_field('response_mappings');
                    d.hide();
                },
            });
            // Show/hide regex pattern depending on selection
            d.fields_dict.transform.df.onchange = () => {
                const val = d.get_value('transform');
                const $wrap = d.fields_dict.regex_pattern.$wrapper;
                if ($wrap) {
                    if (val === 'Regex') { $wrap.show(); } else { $wrap.hide(); }
                }
            };
            // Initialize visibility
            const $wrap = d.fields_dict.regex_pattern.$wrapper; if ($wrap) { $wrap.hide(); }
            d.show();
        });
    });
};

frappe.sap_wrap.open_edit_response_mapping_dialog = function(frm, initial_rowname = null) {
    if (!frm.doc.target_doctype) {
        frappe.msgprint({ message: __("Select Target DocType first."), indicator: "orange" });
        return;
    }
    if (!Array.isArray(frm.doc.response_mappings) || !frm.doc.response_mappings.length) {
        frappe.msgprint({ message: __("Add a Response Mapping row first."), indicator: "orange" });
        return;
    }

    frappe.model.with_doctype(frm.doc.target_doctype, () => {
        const meta = frappe.get_doc('DocType', frm.doc.target_doctype);
        const doc_fields = frappe.sap_wrap.get_fields_options_from_meta(meta);
        const mappingOptions = frm.doc.response_mappings.map(row => ({
            label: `${row.response_path || __("(no path)")} → ${row.target_field || __("(no target)")}`,
            value: row.name,
        }));

        const transformOptions = ['', 'To Int', 'To Float', 'To String', 'Length', 'Digits Only', 'Regex'];

        const d = new frappe.ui.Dialog({
            title: __("Edit Response Mapping"),
            fields: [
                { fieldname: 'mapping', fieldtype: 'Select', label: __("Mapping"), options: mappingOptions, reqd: 1 },
                { fieldname: 'response_path', fieldtype: 'Data', label: __("Response Path"), reqd: 1 },
                { fieldname: 'target_field', fieldtype: 'Select', label: __("Target Field"), options: [''].concat(doc_fields), reqd: 1 },
                { fieldname: 'transform', fieldtype: 'Select', label: __("Transform"), options: transformOptions.join('\n') },
                { fieldname: 'regex_pattern', fieldtype: 'Data', label: __("Regex Pattern") },
                { fieldname: 'default_value', fieldtype: 'Data', label: __("Default Value") },
                { fieldname: 'required', fieldtype: 'Check', label: __("Required") },
            ],
            primary_action_label: __("Apply"),
            primary_action: (values) => {
                const row = frm.doc.response_mappings.find(r => r.name === values.mapping);
                if (!row) {
                    frappe.msgprint({ message: __("Select a mapping."), indicator: "red" });
                    return;
                }
                if (!values.response_path || !values.target_field) {
                    frappe.msgprint({ message: __("Response Path and Target Field are required."), indicator: "red" });
                    return;
                }

                frappe.model.set_value(row.doctype, row.name, {
                    response_path: values.response_path,
                    target_field: values.target_field,
                    transform: values.transform || '',
                    regex_pattern: values.transform && values.transform.toLowerCase() === 'regex' ? (values.regex_pattern || '') : '',
                    default_value: values.default_value || '',
                    required: values.required ? 1 : 0,
                });
                frm.refresh_field('response_mappings');
                d.hide();
            },
        });

        const loadRow = (name) => {
            const row = frm.doc.response_mappings.find(r => r.name === name);
            if (!row) {
                return;
            }
            d.set_value('response_path', row.response_path || '');
            d.set_value('target_field', row.target_field || '');
            d.set_value('transform', row.transform || '');
            d.set_value('regex_pattern', row.regex_pattern || '');
            d.set_value('default_value', row.default_value || '');
            d.set_value('required', row.required ? 1 : 0);
            toggleRegex();
        };

        const toggleRegex = () => {
            const isRegex = (d.get_value('transform') || '').toLowerCase() === 'regex';
            d.toggle_display('regex_pattern', isRegex);
        };

        d.fields_dict.mapping.df.onchange = () => loadRow(d.get_value('mapping'));
        d.fields_dict.transform.df.onchange = toggleRegex;

        d.show();
        const initial = initial_rowname || (mappingOptions[0] && mappingOptions[0].value);
        if (initial) {
            d.set_value('mapping', initial);
            loadRow(initial);
        }
        toggleRegex();
    });
};
