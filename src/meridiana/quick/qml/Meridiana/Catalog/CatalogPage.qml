import QtQuick
import QtQuick.Layouts
import QtQuick.Templates as T
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    property var backend: catalogBackend
    property bool embedded: false
    // R518: inside an M.Dialog that carries its buttons (windowActions, choose()): no row of buttons of its own
    property bool windowButtons: false
    readonly property var windowActions: [
        {text: backend.texts.new},
        {text: backend.texts.copy, enabled: backend.selectedCount > 0},
        {text: backend.texts.import, visible: ["modules", "inverters"].includes(backend.kind)},
        {text: comparing ? backend.texts.compareClose : backend.texts.compareButton, enabled: backend.selectedCount > 0}]
    function windowAction(index) {
        if (index === 0) backend.beginEdit(false)
        else if (index === 1) backend.beginEdit(true)
        else if (index === 2) backend.requestImport()
        else compare()
    }
    implicitWidth: M.ControlMetrics.pageSize.wide.width
    implicitHeight: M.ControlMetrics.pageSize.wide.height
    color: Theme.colors.window
    readonly property var columnWidths: [0.15, 0.31, 0.11, 0.12, 0.16, 0.15]
    Connections { target: root.backend; function onPositioned(row) { catalogList.currentIndex = row; catalogList.positionViewAtIndex(row, ListView.Contain) } }
    property string sortKey: ""
    property bool descending: false
    // «Compare selected products» of the Widgets catalogue (R458 voce 7): the card widens into a table, one column for
    // each of two to four products, the rows whose values differ in strong text.
    property bool comparing: false
    property bool compareAsked: false
    readonly property bool canCompare: root.backend.selectedCount >= 2 && root.backend.selectedCount <= 4
    onCanCompareChanged: if (!canCompare) comparing = false
    function compare() {
        compareAsked = true
        if (comparing) comparing = false
        else if (canCompare) comparing = true
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.embedded ? 0 : Theme.space.XL
        spacing: Theme.space.S
        RowLayout {
            visible: !root.embedded
            Layout.fillWidth: true
            M.Label { text: root.backend.texts.title; textStyle: "display" }
            CatalogChoice {
                objectName: "catalogKind"
                model: root.backend.choices.kinds
                currentIndex: root.backend.choices.kinds.findIndex(o => o.key === root.backend.kind)
                onActivated: root.backend.setKind(currentValue)
            }
            Item { Layout.fillWidth: true }
            M.Button { text: root.backend.texts.import; visible: ["modules", "inverters"].includes(root.backend.kind)
                onClicked: root.backend.requestImport() }
            M.Button { text: root.backend.texts.new; onClicked: root.backend.beginEdit(false) }
        }
        RowLayout {
            Layout.fillWidth: true
            M.TextField {
                id: search
                objectName: "catalogSearch"
                Layout.fillWidth: true
                text: root.backend.filters.text
                placeholderText: root.backend.texts.search
                onTextEdited: root.backend.setFilter("text", text)
            }
            CatalogChoice {
                objectName: "catalogState"
                Layout.preferredWidth: 200
                model: root.backend.choices.states
                currentIndex: root.backend.choices.states.findIndex(o => o.key === root.backend.filters.state)
                onActivated: root.backend.setFilter("state", currentValue)
                Accessible.name: root.backend.texts.state
            }
            // R434 (Daniel, 06/11/2026): it opens on what is current and for Europe; the rest one click away, counted.
            M.Button { objectName: "catalogShowEverything"; visible: root.backend.showAllText !== ""
                text: root.backend.showAllText; tip: root.backend.texts.showAllTip; onClicked: root.backend.showAll() }
            CatalogChoice {
                objectName: "catalogOrigin"
                Layout.preferredWidth: 200
                model: root.backend.choices.origins
                currentIndex: root.backend.choices.origins.findIndex(o => o.key === root.backend.filters.source)
                onActivated: root.backend.setFilter("source", currentValue)
            }
            M.TextField {
                id: maker
                objectName: "catalogMaker"
                Layout.preferredWidth: Math.min(250, root.width / 5)
                text: root.backend.filters.manufacturer
                placeholderText: root.backend.texts.maker
                onTextEdited: { root.backend.setFilter("manufacturer", text); brandPopup.open() }
                onActiveFocusChanged: { if (activeFocus) brandPopup.open() }
                Keys.onDownPressed: { brandList.forceActiveFocus(); brandList.currentIndex = 0 }
                M.Popup {
                    id: brandPopup
                    width: Math.max(M.ControlMetrics.menuWide / 2, maker.width)
                    height: Math.min(M.ControlMetrics.menuTall, brandList.contentHeight + 2 * padding)
                    contentItem: ListView {
                        id: brandList
                        clip: true
                        model: root.backend.brands.filter(n => n.toLocaleLowerCase().includes(maker.text.toLocaleLowerCase()))
                        // R525: the entry of every menu
                        delegate: M.MenuItem {
                            required property string modelData
                            required property int index
                            width: brandList.width
                            text: modelData
                            highlighted: brandList.activeFocus && brandList.currentIndex === index
                            onClicked: { root.backend.setFilter("manufacturer", modelData); brandPopup.close() }
                        }
                        Keys.onReturnPressed: {
                            if (currentIndex >= 0) { root.backend.setFilter("manufacturer", model[currentIndex]); brandPopup.close() }
                        }
                        boundsBehavior: Flickable.StopAtBounds
                    }
                }
            }
            M.Button { text: root.backend.texts.clear; onClicked: root.backend.clearFilters() }
        }
        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            spacing: Theme.space.M
            Row {
                spacing: Theme.space.S
                M.Label { text: root.backend.texts.from; height: Theme.size.CONTROL }
                M.NumberField { width: 125; minimum: 0; maximum: 10000000; decimals: root.backend.kind === "batteries" ? 2 : 0
                    unit: root.backend.kind === "batteries" ? "kWh" : "W"; value: root.backend.filters.low
                    onValueEdited: value => root.backend.setFilter("low", value) }
                M.Label { text: root.backend.texts.to; height: Theme.size.CONTROL }
                M.NumberField { width: 125; minimum: 0; maximum: 10000000; decimals: root.backend.kind === "batteries" ? 2 : 0
                    unit: root.backend.kind === "batteries" ? "kWh" : "W"; value: root.backend.filters.high
                    onValueEdited: value => root.backend.setFilter("high", value) }
            }
            CatalogChoice {
                objectName: "catalogMarket"
                width: M.ControlMetrics.catalogMarketWidth
                model: root.backend.choices.markets
                currentIndex: root.backend.choices.markets.findIndex(o => o.key === root.backend.filters.market)
                onActivated: root.backend.setFilter("market", currentValue)
            }
            CatalogChoice {
                visible: root.backend.kind === "modules"
                model: root.backend.choices.families
                currentIndex: root.backend.choices.families.findIndex(o => o.key === root.backend.filters.family)
                onActivated: root.backend.setFilter("family", currentValue)
            }
            CatalogChoice {
                visible: root.backend.kind === "modules"
                width: M.ControlMetrics.catalogBifacialWidth
                model: root.backend.choices.bifacial
                currentIndex: root.backend.choices.bifacial.findIndex(o => o.key === root.backend.filters.bifacial)
                onActivated: root.backend.setFilter("bifacial", currentValue)
            }
            Row {
                visible: root.backend.kind === "modules"
                spacing: Theme.space.S
                M.Label { text: root.backend.texts.efficiency; height: Theme.size.CONTROL }
                M.NumberField { width: 90; minimum: 0; maximum: 40; decimals: 1; value: root.backend.filters.efficiency_min
                    onValueEdited: value => root.backend.setFilter("efficiency_min", value) }
                M.Label { text: root.backend.texts.length; height: Theme.size.CONTROL }
                M.NumberField { width: 90; minimum: 0; maximum: 4; decimals: 2; value: root.backend.filters.length_max
                    onValueEdited: value => root.backend.setFilter("length_max", value) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.backend.contextText !== "" || root.backend.hiddenText !== ""
            spacing: Theme.space.M
            M.Label { objectName: "catalogContext"; text: root.backend.contextText; visible: text !== ""; textStyle: "secondary"; elide: Text.ElideRight; Layout.maximumWidth: root.width / 2 }
            M.Label { objectName: "catalogHidden"; text: root.backend.hiddenText; visible: text !== ""; textStyle: "secondary"; color: Theme.colors.text2; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Item { Layout.fillWidth: true; visible: root.backend.hiddenText === "" }
            M.Button { objectName: "catalogShowHidden"; visible: root.backend.hiddenText !== ""; text: root.backend.texts.showAll
                onClicked: { root.backend.setFilter("state", ""); root.backend.setFilter("fitting", "all") } }
        }
        Rectangle {
            objectName: "catalogConfirm"
            Layout.fillWidth: true
            visible: root.backend.confirmation !== ""
            implicitHeight: confirmRow.implicitHeight + 2 * Theme.space.S
            radius: Theme.radius.CONTROL
            color: Theme.colors.line_soft
            border.color: Theme.colors.danger; border.width: Theme.line.HAIR
            RowLayout {
                id: confirmRow
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Theme.space.M }
                spacing: Theme.space.M
                M.Label { Layout.fillWidth: true; text: root.backend.confirmation; wrapMode: Text.WordWrap }
                M.Button { text: root.backend.texts.keep; onClicked: root.backend.keepLooking() }
                M.Button { objectName: "catalogAnyway"; text: root.backend.texts.anyway; onClicked: root.backend.chooseAnyway() }
            }
        }
        M.Label { visible: root.backend.error.length > 0 && !root.backend.editing
            text: root.backend.error; color: Theme.colors.danger; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: Theme.space.L
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: Theme.colors.view
                radius: Theme.radius.CARD
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: Theme.size.CONTROL + Theme.text.caption.size + Theme.space.M
                        color: Theme.colors.header
                        visible: catalogList.count > 0
                        Row {
                            // R520: the columns end before the bar's lane, as the rows' do
                            anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                            width: parent.width - catalogBar.room
                            Repeater {
                                model: root.backend.columns
                                Item {
                                    required property int index
                                    required property var modelData
                                    width: parent.width * root.columnWidths[index]
                                    height: parent.height
                                    Column {
                                        anchors.fill: parent; anchors.margins: Theme.space.M
                                        M.Label { width: parent.width; text: modelData.title; textStyle: "secondary"; elide: Text.ElideRight }
                                        M.Label { text: modelData.unit; textStyle: "caption"; color: Theme.colors.muted }
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            root.descending = root.sortKey === modelData.key ? !root.descending : false
                                            root.sortKey = modelData.key
                                            root.backend.sortBy(modelData.key, root.descending)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    ListView {
                        id: catalogList
                        objectName: "catalogList"
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true
                        model: root.backend.model
                        reuseItems: true
                        cacheBuffer: 80
                        boundsBehavior: Flickable.StopAtBounds
                        keyNavigationEnabled: true
                        Keys.onReleased: event => {
                            if ([Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown].includes(event.key)) {
                                if ((event.modifiers & Qt.ShiftModifier) !== 0) root.backend.selectRange(currentIndex)
                                else root.backend.select(currentIndex, false)
                            }
                        }
                        Keys.onReturnPressed: root.backend.choose()
                        Keys.onPressed: event => {
                            if (event.key === Qt.Key_End) {
                                currentIndex = count - 1; positionViewAtEnd(); root.backend.select(currentIndex, false); event.accepted = true
                            } else if (event.key === Qt.Key_Home) {
                                currentIndex = 0; positionViewAtBeginning(); root.backend.select(currentIndex, false); event.accepted = true
                            }
                        }
                        delegate: Rectangle {
                            id: productRow
                            required property int index
                            required property var cells
                            required property string identity
                            required property bool selected
                            required property string rowKind
                            required property bool open
                            required property string stateKey
                            required property string fit
                            required property string why
                            objectName: "catalogProductRow"
                            width: catalogList.width
                            height: Math.ceil(rowMetrics.height) + 8
                            FontMetrics { id: rowMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.type.BODY }
                            color: selected ? Theme.colors.select_bg :
                                   rowMouse.containsMouse ? Theme.colors.hover : "transparent"
                            Row {
                                anchors.fill: parent
                                Repeater {
                                    model: productRow.cells
                                    Item {
                                        required property int index
                                        required property string modelData
                                        width: (productRow.width - catalogBar.room) * root.columnWidths[index]
                                        height: productRow.height
                                        M.Label {
                                            id: rowText
                                            anchors.fill: parent; anchors.leftMargin: Theme.space.M + (index === 1 && productRow.rowKind !== "" ? Theme.size.CHIP : 0); anchors.rightMargin: Theme.space.M
                                            text: modelData
                                            horizontalAlignment: index === 2 ? Text.AlignRight : Text.AlignLeft
                                            elide: Text.ElideRight
                                            textStyle: productRow.rowKind === "family" && index <= 1 ? "strong" : "body"
                                            color: productRow.rowKind === "unread" || productRow.fit === "no" ? Theme.colors.muted
                                                   : index === 5 && productRow.stateKey === "discontinued" ? Theme.colors.danger
                                                   : index === 5 && productRow.stateKey !== "current" ? Theme.colors.text2 : Theme.colors.text
                                        }
                                        M.Icon {        // R518: a drawn arrow, not «▾ ▸» of a font that may lack them
                                            visible: index === 1 && productRow.rowKind === "family"
                                            anchors { left: parent.left; leftMargin: Theme.space.M; verticalCenter: parent.verticalCenter }
                                            width: Theme.icon.CONTROL; height: width
                                            iconName: "control:chevron-down"; rotation: productRow.open ? 0 : -90
                                            Accessible.role: Accessible.Button
                                            Accessible.name: productRow.open ? root.backend.texts.close : root.backend.texts.open
                                            TapHandler { onTapped: root.backend.toggleFamily(productRow.index) }
                                        }
                                    }
                                }
                            }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line_soft }
                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: mouse => {
                                    catalogList.currentIndex = productRow.index
                                    catalogList.forceActiveFocus()
                                    if ((mouse.modifiers & Qt.ShiftModifier) !== 0) root.backend.selectRange(productRow.index)
                                    else root.backend.select(productRow.index, (mouse.modifiers & Qt.ControlModifier) !== 0)
                                }
                                onDoubleClicked: root.backend.choose()
                            }
                            M.ToolTip { visible: rowMouse.containsMouse && productRow.why !== ""; text: productRow.why }
                        }
                        T.ScrollBar.vertical: M.ScrollBar { id: catalogBar }
                        M.Label {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 2 * Theme.space.XL, Theme.size.READING)
                            text: root.backend.busy ? root.backend.texts.loading : root.backend.texts.empty
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            visible: catalogList.count === 0
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; Layout.margins: Theme.space.M
                        M.Label { objectName: "catalogCount"; text: root.backend.countText; textStyle: "secondary" }
                        Item { Layout.fillWidth: true }
                        M.Label { visible: root.backend.busy && catalogList.count > 0; text: root.backend.texts.loading; textStyle: "secondary" }
                    }
                }
            }
            Rectangle {
                objectName: "catalogCard"
                Layout.preferredWidth: root.comparing ? Math.max(Math.min(400, root.width * 0.32), root.width * 0.6)
                                                      : Math.min(400, root.width * 0.32)
                Layout.fillHeight: true
                color: Theme.colors.card; radius: Theme.radius.CARD
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: Theme.space.L
                    M.Label { text: root.backend.texts.details; textStyle: "title"; visible: !root.embedded }
                    M.Label { text: root.backend.selectedNames.join(" / "); textStyle: "strong"
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; visible: text.length > 0 }
                    M.Label { text: root.backend.texts.compare; textStyle: "caption"; color: Theme.colors.muted
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; visible: root.backend.selectedCount > 1 && !root.comparing }
                    M.Label { objectName: "catalogCompareHint"; text: root.backend.texts.compareHint; textStyle: "caption"
                        color: Theme.colors.text2; Layout.fillWidth: true; wrapMode: Text.WordWrap
                        visible: root.compareAsked && !root.canCompare }
                    Row {
                        objectName: "catalogCompareHeader"
                        visible: root.comparing
                        Layout.fillWidth: true
                        spacing: Theme.space.XS
                        Item { width: details.width*.44; height: 1 }
                        Repeater {
                            model: root.comparing ? root.backend.selectedNames : []
                            M.Label { required property string modelData; text: modelData; textStyle: "strong"
                                width: (details.width*.56-Theme.space.XS)/Math.max(1, root.backend.selectedCount); wrapMode: Text.WrapAnywhere }
                        }
                    }
                    M.Label { text: root.backend.texts.cec; textStyle: "caption"; color: Theme.colors.muted
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; visible: root.backend.selectedRecord.source === "cec" }
                    M.Label { text: root.backend.texts.noSelection; textStyle: "secondary"; color: Theme.colors.muted
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; visible: root.backend.selectedCount === 0 }
                    ColumnLayout {
                        objectName: "catalogLifecycle"
                        Layout.fillWidth: true
                        visible: root.backend.selectedCount === 1
                        spacing: Theme.space.XXS
                        M.Label { Layout.fillWidth: true; textStyle: "strong"; text: root.backend.selectedState.text || ""
                            color: root.backend.selectedState.state === "discontinued" ? Theme.colors.danger : Theme.colors.text }
                        M.Label { Layout.fillWidth: true; textStyle: "caption"; color: Theme.colors.text2; wrapMode: Text.Wrap; text: root.backend.selectedState.detail || "" }
                        M.Label { Layout.fillWidth: true; textStyle: "caption"; color: Theme.colors.danger; wrapMode: Text.Wrap
                            visible: text !== ""; text: root.backend.selectedState.unread || (root.backend.selectedState.reasons || []).join("\n") }
                        M.Label { Layout.fillWidth: true; textStyle: "caption"; color: Theme.colors.text2; wrapMode: Text.Wrap
                            visible: text !== ""; text: (root.backend.selectedState.passed || []).join("; ") }
                    }
                    ListView {
                        id: details
                        Layout.fillHeight: true; Layout.fillWidth: true
                        clip: true; spacing: Theme.space.XS
                        T.ScrollBar.vertical: M.ScrollBar { id: detailsBar }
                        model: root.backend.details
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: Row {
                            id: detailField
                            required property var modelData
                            readonly property bool differs: modelData.values.length > 1 && modelData.values.some(v => v !== modelData.values[0])
                            width: details.width - detailsBar.room
                            spacing: Theme.space.XS
                            M.Label { width: (details.width - detailsBar.room)*.44; text: modelData.label; color: Theme.colors.text2; wrapMode: Text.Wrap
                                textStyle: root.comparing && detailField.differs ? "strong" : "body" }
                            Repeater {
                                model: modelData.values
                                M.Label { required property string modelData; text: modelData
                                    textStyle: root.comparing && detailField.differs ? "strong" : "body"
                                    width: (details.width*.56-Theme.space.XS)/Math.max(1, detailField.modelData.values.length); wrapMode: Text.WrapAnywhere
                                    color: detailField.modelData.key === "datasheet_url" ? Theme.colors.accent : Theme.colors.text
                                    TapHandler { enabled: detailField.modelData.key === "datasheet_url"
                                        onTapped: root.backend.openSource(parent.text) }
                                }
                            }
                        }
                    }
                    M.Button { visible: !root.embedded; objectName: "catalogCompare"
                        text: root.comparing ? root.backend.texts.compareClose : root.backend.texts.compareButton
                        enabled: root.backend.selectedCount > 0; onClicked: root.compare() }
                    M.Button { visible: !root.embedded; text: root.backend.texts.copy; enabled: root.backend.selectedCount > 0
                        onClicked: root.backend.beginEdit(true) }
                    M.Button { visible: !root.embedded; objectName: "catalogChoose"; text: root.backend.texts.choose
                        enabled: root.backend.canChoose; onClicked: root.backend.choose() }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.embedded && !root.windowButtons
            spacing: Theme.space.S
            M.Button { text: root.backend.texts.new; onClicked: root.backend.beginEdit(false) }
            M.Button { text: root.backend.texts.copy; enabled: root.backend.selectedCount>0; onClicked: root.backend.beginEdit(true) }
            M.Button { visible: ["modules","inverters"].includes(root.backend.kind); text: root.backend.texts.import; onClicked: root.backend.requestImport() }
            M.Button { objectName: "catalogCompareEmbedded"
                text: root.comparing ? root.backend.texts.compareClose : root.backend.texts.compareButton
                enabled: root.backend.selectedCount > 0; onClicked: root.compare() }
            Item { Layout.fillWidth: true }
            M.Button { objectName: "catalogAccept"; text: root.backend.texts.choose; enabled: root.backend.canChoose; onClicked: root.backend.choose() }
        }
    }
    CatalogEditor { backend: root.backend; parent: T.Overlay.overlay }
}
