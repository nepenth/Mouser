import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  Minimal first-exposure controls for keyboard middle-path features
    (BACKLIGHT2 and K375S FN inversion).

    This component is intentionally small and will be expanded in later
    micro-chunks (full KeyboardPage, per-device persistence, key diversion opt-in, etc.).

    All changes made here are host-side only and temporary (lost on
    reconnect or host switch). This is strongly communicated to the user.
*/

Item {
    id: root
    visible: backend.keyboardBacklightSupported || backend.keyboardFnInversionSupported
    implicitHeight: content.implicitHeight + 32
    Layout.fillWidth: true

    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    // Local cached state so we don't hammer the device on every paint
    property bool backlightEnabled: false
    property int backlightLevel: 50
    property bool fnSwapActive: false

    // Polish state for 005.2
    property bool refreshing: false
    property string lastError: ""

    Component.onCompleted: {
        refreshFromDevice()
    }

    function refreshFromDevice() {
        if (refreshing) return
        refreshing = true
        lastError = ""

        if (backend.keyboardBacklightSupported) {
            var bl = backend.readBacklight()
            if (bl && bl.length >= 2) {
                var en = bl[0]
                var lvl = bl[1]
                backlightEnabled = (en !== null && en !== undefined) ? !!en : false
                backlightLevel = (lvl !== null && lvl !== undefined) ? lvl : 50
            }
        }
        if (backend.keyboardFnInversionSupported) {
            var fnVal = backend.readFnInversion()
            fnSwapActive = (fnVal !== null && fnVal !== undefined) ? !!fnVal : false
        }

        refreshing = false
    }

    function applyBacklight() {
        if (!backend.keyboardBacklightSupported) return
        var ok = backend.setBacklight(backlightEnabled, backlightLevel)
        if (!ok) {
            showError("Failed to apply backlight (temporary change)")
        }
    }

    function applyFnInversion() {
        if (!backend.keyboardFnInversionSupported) return
        var ok = backend.setFnInversion(fnSwapActive)
        if (!ok) {
            showError("Failed to apply Fn inversion (temporary change)")
        }
    }

    function showError(msg) {
        lastError = msg
        errorClearTimer.restart()
    }

    Timer {
        id: errorClearTimer
        interval: 3800
        repeat: false
        onTriggered: lastError = ""
    }

    // Debounce timer for brightness slider (prevents HID++ spam)
    Timer {
        id: brightnessDebounce
        interval: 350
        repeat: false
        onTriggered: {
            if (backend.keyboardBacklightSupported && !refreshing) {
                backend.setBacklight(backlightEnabled, backlightLevel)
            }
        }
    }

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 16
        radius: Theme.radius
        color: root.theme.bgCard
        border.width: 1
        border.color: root.theme.border

        ColumnLayout {
            id: content
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 20
            }
            spacing: 16

            // ── Header with strong temporary warning ─────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Keyboard – Host-side Controls"
                    font {
                        family: uiState.fontFamily
                        pixelSize: 16
                        bold: true
                    }
                    color: root.theme.textPrimary
                }

                Rectangle {
                    Layout.preferredHeight: 24
                    Layout.preferredWidth: tempWarning.implicitWidth + 20
                    radius: 6
                    color: Qt.rgba(1.0, 0.6, 0.0, root.theme.dark ? 0.25 : 0.18)

                    Text {
                        id: tempWarning
                        anchors.centerIn: parent
                        text: "TEMPORARY — lost on reconnect or host switch"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 11
                            bold: true
                        }
                        color: "#E68A00"
                    }
                }

                // Refreshing indicator (005.2 polish)
                Text {
                    visible: root.refreshing
                    text: "Refreshing…"
                    font { family: uiState.fontFamily; pixelSize: 12; italic: true }
                    color: root.theme.textSecondary
                }

                Item { Layout.fillWidth: true }
            }

            // Error feedback row (005.2)
            Text {
                visible: root.lastError !== ""
                text: root.lastError
                font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                color: "#D32F2F"
                Layout.leftMargin: 4
            }

            // ── Backlight section ────────────────────────────────────────
            Column {
                visible: backend.keyboardBacklightSupported
                width: parent.width
                spacing: 10

                RowLayout {
                    width: parent.width

                    Column {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: "Backlight"
                            font {
                                family: uiState.fontFamily
                                pixelSize: 14
                                bold: true
                            }
                            color: root.theme.textPrimary
                        }
                        Text {
                            text: "Onboard profile lighting (host override only)"
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: root.theme.textSecondary
                        }
                    }

                    Switch {
                        checked: root.backlightEnabled
                        Material.accent: root.theme.accent
                        enabled: !root.refreshing
                        onClicked: {
                            root.backlightEnabled = checked
                            root.applyBacklight()
                        }
                    }
                }

                // Brightness slider (only meaningful when enabled)
                Column {
                    visible: root.backlightEnabled
                    width: parent.width
                    spacing: 6

                    Text {
                        text: "Brightness"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 11
                            bold: true
                            letterSpacing: 0.6
                        }
                        color: root.theme.textDim
                    }

                    RowLayout {
                        width: parent.width
                        spacing: 10

                        Text {
                            text: "0"
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: root.theme.textDim
                        }

                        Slider {
                            id: brightnessSlider
                            Layout.fillWidth: true
                            from: 0
                            to: 100
                            stepSize: 5
                            value: root.backlightLevel
                            enabled: !root.refreshing

                            onMoved: {
                                root.backlightLevel = Math.round(value)
                                // Debounced apply — only hits the device after user stops moving
                                brightnessDebounce.restart()
                            }
                        }

                        Text {
                            text: "100"
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: root.theme.textDim
                        }

                        Rectangle {
                            Layout.preferredWidth: 56
                            Layout.preferredHeight: 28
                            radius: 6
                            color: root.theme.accentDim

                            Text {
                                anchors.centerIn: parent
                                text: root.backlightLevel + "%"
                                font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                                color: root.theme.textPrimary
                            }
                        }
                    }
                }
            }

            // ── FN Inversion section ─────────────────────────────────────
            RowLayout {
                visible: backend.keyboardFnInversionSupported
                Layout.fillWidth: true
                spacing: 12

                Column {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: "Fn / Fx Swap"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 14
                            bold: true
                        }
                        color: root.theme.textPrimary
                    }
                    Text {
                        text: "Swap Fn and Fx key behavior (host view)"
                        font { family: uiState.fontFamily; pixelSize: 11 }
                        color: root.theme.textSecondary
                    }
                }

                Switch {
                    checked: root.fnSwapActive
                    Material.accent: root.theme.accent
                    enabled: !root.refreshing
                    onClicked: {
                        root.fnSwapActive = checked
                        root.applyFnInversion()
                    }
                }
            }

            // Refresh button (useful after host switch)
            RowLayout {
                Layout.fillWidth: true

                Item { Layout.fillWidth: true }

                Button {
                    text: "Refresh from device"
                    font { family: uiState.fontFamily; pixelSize: 12 }
                    enabled: !root.refreshing
                    onClicked: root.refreshFromDevice()
                }
            }
        }
    }

    // React to capability changes (device connect/disconnect, host switch)
    Connections {
        target: backend
        function onKeyboardBacklightSupportedChanged() { root.refreshFromDevice() }
        function onKeyboardFnInversionSupportedChanged() { root.refreshFromDevice() }
    }
}
