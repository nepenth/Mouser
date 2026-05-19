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
