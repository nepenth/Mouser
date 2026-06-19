import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  Minimal first slice of a dedicated Keyboard page (TASK-005 005.3).
    Reuses the existing KeyboardControls component.

    This page only shows useful content when a supported keyboard
    (e.g. MX Mechanical Mini) is connected. The controls themselves
    already handle hiding when unsupported.
*/

Item {
    id: keyboardPage
    readonly property var theme: Theme.palette(uiState.darkMode)

    readonly property bool anyDiversionEnabled:
        allowDiversionBacklightSwitch.checked
        || allowDiversionVolumeSwitch.checked
        || allowDiversionMuteSwitch.checked
        || allowDiversionSearchSwitch.checked

    function refreshPermissionToggles() {
        if (backend.keyboardBacklightSupported || backend.keyboardFnInversionSupported) {
            allowBacklightSwitch.checked = backend.getDeviceKeyboardMiddlePathSetting("allow_host_backlight")
            allowFnSwitch.checked = backend.getDeviceKeyboardMiddlePathSetting("allow_fn_inversion")
            allowDiversionBacklightSwitch.checked = backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_backlight")
            allowDiversionVolumeSwitch.checked = backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_volume")
            allowDiversionMuteSwitch.checked = backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_mute")
            allowDiversionSearchSwitch.checked = backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_search")
        }
    }

    Connections {
        target: backend
        function onDeviceInfoChanged() { keyboardPage.refreshPermissionToggles() }
        function onHidFeaturesReadyChanged() { keyboardPage.refreshPermissionToggles() }
        function onSelectedDeviceKeyChanged() { keyboardPage.refreshPermissionToggles() }
    }

    ColumnLayout {
        anchors {
            fill: parent
            margins: 24
        }
        spacing: 16

        // Page header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "Keyboard"
                font {
                    family: uiState.fontFamily
                    pixelSize: 22
                    bold: true
                }
                color: keyboardPage.theme.textPrimary
            }

            // Strong temporary/host-side warning badge (mirrors the one in KeyboardControls)
            Rectangle {
                visible: backend.keyboardBacklightSupported || backend.keyboardFnInversionSupported
                Layout.preferredHeight: 26
                Layout.preferredWidth: warningLabel.implicitWidth + 24
                radius: 6
                color: Qt.rgba(1.0, 0.6, 0.0, keyboardPage.theme.dark ? 0.28 : 0.2)

                Text {
                    id: warningLabel
                    anchors.centerIn: parent
                    text: "Host-side only — changes are temporary"
                    font {
                        family: uiState.fontFamily
                        pixelSize: 12
                        bold: true
                    }
                    color: "#E68A00"
                }
            }

            Item { Layout.fillWidth: true }
        }

        // Device status block (005.4) — only for supported middle-path keyboards
        Column {
            visible: backend.keyboardBacklightSupported || backend.keyboardFnInversionSupported
            Layout.fillWidth: true
            spacing: 2
            Layout.topMargin: 4

            Text {
                text: "Device: " + backend.deviceDisplayName
                font {
                    family: uiState.fontFamily
                    pixelSize: 13
                }
                color: keyboardPage.theme.textSecondary
            }

            Text {
                text: "Connection: " + backend.connectionType
                font {
                    family: uiState.fontFamily
                    pixelSize: 13
                }
                color: keyboardPage.theme.textSecondary
            }

            Text {
                text: backend.batteryLevel >= 0
                      ? "Battery: " + backend.batteryLevel + "%"
                      : "Battery: Not reported"
                font {
                    family: uiState.fontFamily
                    pixelSize: 13
                }
                color: keyboardPage.theme.textSecondary
            }
        }

        // Per-device host control permissions (006.3)
        Column {
            visible: backend.keyboardBacklightSupported || backend.keyboardFnInversionSupported
            Layout.fillWidth: true
            spacing: 8
            Layout.topMargin: 12

            Text {
                text: "Host Control Permissions"
                font {
                    family: uiState.fontFamily
                    pixelSize: 14
                    bold: true
                }
                color: keyboardPage.theme.textPrimary
            }

            Text {
                text: "These preferences are stored per-device and survive host switches."
                font {
                    family: uiState.fontFamily
                    pixelSize: 11
                }
                color: keyboardPage.theme.textSecondary
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Allow host backlight control"
                    font { family: uiState.fontFamily; pixelSize: 13 }
                    color: keyboardPage.theme.textPrimary
                }

                Switch {
                    id: allowBacklightSwitch
                    checked: backend.getDeviceKeyboardMiddlePathSetting("allow_host_backlight")
                    Material.accent: keyboardPage.theme.accent
                    onClicked: {
                        backend.setDeviceKeyboardMiddlePathSetting("allow_host_backlight", checked)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Allow host FN inversion"
                    font { family: uiState.fontFamily; pixelSize: 13 }
                    color: keyboardPage.theme.textPrimary
                }

                Switch {
                    id: allowFnSwitch
                    checked: backend.getDeviceKeyboardMiddlePathSetting("allow_fn_inversion")
                    Material.accent: keyboardPage.theme.accent
                    onClicked: {
                        backend.setDeviceKeyboardMiddlePathSetting("allow_fn_inversion", checked)
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: "Key Diversion (opt-in)"
                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                color: keyboardPage.theme.textPrimary
            }

            Text {
                Layout.fillWidth: true
                text: "Diverted keys stop working as normal media/backlight keys on the onboard profile. Assign Mouser actions in button mappings instead."
                font { family: uiState.fontFamily; pixelSize: 10; italic: true }
                color: keyboardPage.theme.textSecondary
                wrapMode: Text.WordWrap
            }

            Rectangle {
                visible: anyDiversionEnabled
                Layout.fillWidth: true
                Layout.preferredHeight: diversionWarningLabel.implicitHeight + 16
                radius: 6
                color: Qt.rgba(0.9, 0.2, 0.2, keyboardPage.theme.dark ? 0.28 : 0.15)

                Text {
                    id: diversionWarningLabel
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    text: "Warning: key diversion is enabled. Selected keys are captured by Mouser and will not perform their normal onboard function."
                    font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                    color: "#D94A4A"
                    wrapMode: Text.WordWrap
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Allow diversion of Backlight Up/Down keys"
                    font { family: uiState.fontFamily; pixelSize: 13 }
                    color: keyboardPage.theme.textPrimary
                }

                Switch {
                    id: allowDiversionBacklightSwitch
                    checked: backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_backlight")
                    Material.accent: keyboardPage.theme.accent
                    onClicked: {
                        backend.setDeviceKeyboardMiddlePathSetting("allow_diversion_backlight", checked)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Allow diversion of Volume Up/Down keys"
                    font { family: uiState.fontFamily; pixelSize: 13 }
                    color: keyboardPage.theme.textPrimary
                }

                Switch {
                    id: allowDiversionVolumeSwitch
                    checked: backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_volume")
                    Material.accent: keyboardPage.theme.accent
                    onClicked: {
                        backend.setDeviceKeyboardMiddlePathSetting("allow_diversion_volume", checked)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Allow diversion of Mute key"
                    font { family: uiState.fontFamily; pixelSize: 13 }
                    color: keyboardPage.theme.textPrimary
                }

                Switch {
                    id: allowDiversionMuteSwitch
                    checked: backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_mute")
                    Material.accent: keyboardPage.theme.accent
                    onClicked: {
                        backend.setDeviceKeyboardMiddlePathSetting("allow_diversion_mute", checked)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Allow diversion of Search key"
                    font { family: uiState.fontFamily; pixelSize: 13 }
                    color: keyboardPage.theme.textPrimary
                }

                Switch {
                    id: allowDiversionSearchSwitch
                    checked: backend.getDeviceKeyboardMiddlePathSetting("allow_diversion_search")
                    Material.accent: keyboardPage.theme.accent
                    onClicked: {
                        backend.setDeviceKeyboardMiddlePathSetting("allow_diversion_search", checked)
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: "Host-side only. Changes are temporary. Requires explicit opt-in."
                font { family: uiState.fontFamily; pixelSize: 10; italic: true }
                color: keyboardPage.theme.textSecondary
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Apply KVM-friendly defaults (host backlight + FN on, all key diversion off)."
                    font { family: uiState.fontFamily; pixelSize: 11 }
                    color: keyboardPage.theme.textSecondary
                    wrapMode: Text.WordWrap
                }

                Button {
                    text: "KVM mode"
                    font { family: uiState.fontFamily; pixelSize: 12 }
                    onClicked: {
                        if (backend.applyKvmPreset()) {
                            refreshPermissionToggles()
                        }
                    }
                }
            }
        }

        // Helpful subtitle when no supported keyboard is present
        Text {
            visible: !(backend.keyboardBacklightSupported || backend.keyboardFnInversionSupported)
            Layout.fillWidth: true
            text: "No supported keyboard detected.\nConnect an MX Mechanical Mini (or similar) to see host-side controls here."
            font {
                family: uiState.fontFamily
                pixelSize: 14
            }
            color: keyboardPage.theme.textSecondary
            wrapMode: Text.WordWrap
        }

        // The actual controls (reused from the earlier work)
        KeyboardControls {
            Layout.fillWidth: true
            Layout.topMargin: 8
        }

        Item { Layout.fillHeight: true }
    }
}
