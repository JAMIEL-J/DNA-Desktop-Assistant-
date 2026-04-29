import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView


def main() -> int:
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("DNA UI (WebView)")
    window.resize(1400, 900)

    view = QWebEngineView()
    html_path = Path(__file__).resolve().parent / "ui" / "dna_ui.html"
    view.load(QUrl.fromLocalFile(str(html_path)))

    window.setCentralWidget(view)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
