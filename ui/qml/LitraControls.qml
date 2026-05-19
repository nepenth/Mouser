import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  First minimal UI surface for Litra Beam illumination (TASK-008 008.5).
    Small, self-contained card with on/off + brightness.
    All changes are host-side only and temporary (lost on reconnect or host switch).
*/

Item {
    id: root
    visible: backend.hasLitraBeam
    implicitHeight: content.implicitHeight + 32
    Layout.fillWidth: true

    readonly property var theme: Theme.palette(uiState.darkMode)

    // Local cached state
    property bool litraEnabled: false
    property int litraBrightness: 50

    Component.onCompleted: {
        refreshFromDevice()
    }

    function refreshFromDevice() {
        if (!backend.hasLitraBeam) return
        var state = backend.readLitraIllumination()
        if (state && state.length >= 2) {
            litraEnabled = !!state[0]
            litraBrightness = (state[1] !== null && state[1] !== undefined) ? state[1] : 50
        }
    }

    function applyIllumination() {
        if (!backend.hasLitraBeam) return
        backend.setLitraIllumination(litraEnabled, litraBrightness)
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

            // Header with temporary warning
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Litra Beam"
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
                        text: "Host-side only — temporary"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 11
                            bold: true
                        }
                        color: "#E68A00"
                    }
                }

                Item { Layout.fillWidth: true }
            }

            // On/Off
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: "Light"
                    font {
                        family: uiState.fontFamily
                        pixelSize: 14
                        bold: true
                    }
                    color: root.theme.textPrimary
                }

                Switch {
                    checked: root.litraEnabled
                    Material.accent: root.theme.accent
                    onClicked: {
                        root.litraEnabled = checked
                        root.applyIllumination()
                    }
                }
            }

            // Brightness (only when enabled)
            Column {
                visible: root.litraEnabled
                Layout.fillWidth: true
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
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: "0"
                        font { family: uiState.fontFamily; pixelSize: 11 }
                        color: root.theme.textDim
                    }

                    Slider {
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        stepSize: 5
                        value: root.litraBrightness
                        onMoved: {
                            root.litraBrightness = Math.round(value)
                            root.applyIllumination()
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
                            text: root.litraBrightness + "%"
                            font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                            color: root.theme.textPrimary
                        }
                    }
                }
            }

            // Refresh (useful after host switch)
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "Refresh"
                    font { family: uiState.fontFamily; pixelSize: 12 }
                    onClicked: root.refreshFromDevice()
                }
            }
        }
    }
}
