import os
import sys
from threading import Thread, Event

import gi
import sh

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import GLib

gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as appindicator

gi.require_version('Notify', '0.7')
from gi.repository import Notify

APPINDICATOR_ID = "gnome-tlp"
DIR = os.path.dirname(os.path.abspath(__file__))
Notify.init(APPINDICATOR_ID)

terminal = sh.Command("gnome-terminal").bake("--", "sh", "-c")
sudo = sh.sudo.bake(non_interactive=True)
stat = sudo.bake("tlp-stat")
tlp = sudo.bake("tlp")


def get_icon_path(mode="bat-eco-aut"):
    return os.path.join(DIR, "img", "%s.svg" % mode)


class Indicator(object):
    def __init__(self):
        self.indicator = appindicator.Indicator.new(
            APPINDICATOR_ID, "battery",
            appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.menu = gtk.Menu()

        self.items = []
        for key in ("Auto", "AC", "BAT"):
            item = gtk.RadioMenuItem.new_with_label(self.items, key)
            item.connect("activate", getattr(self, f"tlp_{key.lower()}"))
            self.menu.append(item)
            self.items.append(item)
            setattr(self, f"item_{key.lower()}", item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        self.running = Event()
        self.update_now = Event()

        self.mode = "BAT"
        self.is_auto = True
        self.is_ac_mode = False
        self.has_ac = False

    def notify_change(self, msg):
        n = Notify.Notification.new("TLP state changed via widget", msg.strip(), self.get_icon())
        n.set_timeout(Notify.EXPIRES_DEFAULT)
        n.set_urgency(Notify.Urgency.NORMAL)
        n.show()

    def tlp_auto(self, source):
        if not self.is_auto:
            msg = tlp.start()  # terminal("sudo tlp start; read")
            self.is_auto = True
            self.notify_change(msg)
            self.update_now.set()

    def tlp_ac(self, source):
        if self.is_auto or not self.is_ac_mode:
            msg = tlp.ac()  # terminal("sudo tlp ac; read")
            self.is_auto = False
            self.is_ac_mode = True
            self.notify_change(msg)
            self.update_now.set()

    def tlp_bat(self, *args, **kwargs):
        if self.is_auto or self.is_ac_mode:
            msg = tlp.bat()  # terminal("sudo tlp bat; read")
            self.is_auto = False
            self.is_ac_mode = False
            self.notify_change(msg)
            self.update_now.set()

    def get_config(self, *args, **kwargs):
        section = None
        conf = {}
        for line in stat(*args, **kwargs).splitlines():
            if not line:
                continue
            _, _, version = line.partition("--- TLP ")
            if version:
                conf["version"] = version.strip("- ")
                continue
            if line.startswith("+++"):
                section = line.strip("+: ")
                assert section not in conf
                conf[section] = {}
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                conf[section][key.strip()] = value.strip()
                continue
            print("Could not parse line '{}'".format(line), file=sys.stderr)
        return conf

    def update_status(self, conf=None):
        if not conf:
            conf = self.get_config("-s")['TLP Status']
        self.mode = conf["Mode"]
        self.is_auto = "manual" not in conf["Mode"]
        self.is_ac_mode = "ac" in conf["Mode"].lower()
        self.has_ac = "ac" in conf["Power source"].lower()

    def get_icon(self):
        return get_icon_path("-".join((
            "ac" if self.has_ac else "bat",
            "pow" if self.is_ac_mode else "eco",
            "aut" if self.is_auto else "fix",
        )))

    def update_display(self):
        self.item_auto.set_label(f"Auto ({'AC' if self.has_ac else 'BAT'})")
        if self.is_auto:
            self.item_auto.set_active(True)
        elif self.is_ac_mode:
            self.item_ac.set_active(True)
        else:
            self.item_bat.set_active(True)
        self.indicator.set_icon_full(self.get_icon(), self.mode)

    def auto_update(self):
        self.running.wait()
        while self.running.is_set():
            self.update_status()
            GLib.idle_add(self.update_display)
            self.update_now.clear()
            self.update_now.wait(10)  # CONFIG["update_interval"]

    def main(self):
        t = Thread(target=self.auto_update, daemon=True)
        try:
            t.start()
            GLib.idle_add(self.running.set)
            GLib.idle_add(self.update_now.set)
            gtk.main()
        finally:
            self.update_now.set()
            self.running.clear()
            t.join()

    def quit(self):
        gtk.main_quit()


def run():
    gtk.init()
    Indicator().main()

if __name__ == "__main__":
    run()
