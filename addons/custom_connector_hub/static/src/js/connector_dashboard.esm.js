/** @odoo-module */
import { registry } from "@web/core/registry";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class ConnectorRunKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.statusClass = `o_connector_status_${this.props.record.data.status}`;
    }
}

registry.category("views").add("connector_run_kanban", {
    ...registry.category("views").get("kanban"),
    Controller: registry.category("views").get("kanban").Controller,
    Record: ConnectorRunKanbanRecord,
});
