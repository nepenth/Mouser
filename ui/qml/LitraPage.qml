import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  Dedicated Litra Beam page (TASK-008 008.7).
    Reuses the existing LitraControls component.

    This page only shows useful content when a supported Litra device
    (e.g. Litra Beam) is connected. The controls themselves already
    handle capability gating when used as a footer; here we force them
    visible so the page layout stays stable.
*/

Item {
    id: litraPage
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
                text: "Lights"
                font {
                    family: uiState.fontFamily
                    pixelSize: 22
                    bold: true
                }
                color: litraPage.theme.textPrimary
            }

            // Strong temporary/host-side warning badge (mirrors LitraControls)
            Rectangle {
                visible: backend.hasLitraIlluminationSupported
                Layout.preferredHeight: 26
                Layout.preferredWidth: warningLabel.implicitWidth + 24
                radius: 6
                color: Qt.rgba(1.0, 0.6, 0.0, litraPage.theme.dark ? 0.28 : 0.2)

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

        // Device status block — only for supported Litra devices
        Column {
            visible: backend.hasLitraIlluminationSupported
            Layout.fillWidth: true
            spacing: 2
            Layout.topMargin: 4

            Text {
                text: "Device: " + backend.deviceDisplayName
                font {
                    family: uiState.fontFamily
                    pixelSize: 13
                }
                color: litraPage.theme.textSecondary
            }

            Text {
                text: "Connection: " + backend.connectionType
                font {
                    family: uiState.fontFamily
                    pixelSize: 13
                }
                color: litraPage.theme.textSecondary
            }

            Text {
                text: backend.batteryLevel >= 0
                      ? "Battery: " + backend.batteryLevel + "%"
                      : "Battery: Not reported"
                font {
                    family: uiState.fontFamily
                    pixelSize: 13
                }
                color: litraPage.theme.textSecondary
            }
        }

        // Helpful subtitle when no supported Litra device is present
        Text {
            visible: !backend.hasLitraIlluminationSupported
            Layout.fillWidth: true
            text: "No supported Litra device detected.\nConnect a Litra Beam to see host-side illumination controls here."
            font {
                family: uiState.fontFamily
                pixelSize: 14
            }
            color: litraPage.theme.textSecondary
            wrapMode: Text.WordWrap
        }

        // The actual controls (reused from the footer quick-access card).
        // Override root visible so the page instance stays usable regardless of
        // the footer currentPage guard in Main.qml.
        LitraControls {
            visible: true
            Layout.fillWidth: true
            Layout.topMargin: 8
        }

        Item { Layout.fillHeight: true }
    }
}