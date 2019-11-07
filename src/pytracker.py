#!/usr/bin/python3
from gi import require_version
require_version('Notify', '0.7')
require_version('Gtk', '3.0')
from gi.repository import Notify, GLib, Gtk
from subprocess import Popen, PIPE
from time import sleep
import os, re
from shutil import which

class TaskNotify:
    def __init__(self):
        Notify.init('Task Tracker')
        self.notifications = []
        self.windows = []
        self.work = []
        self.load_work()
        if len(self.work) > 0:
            self.request_work(self.work[-1])
        else:
            self.request_task()

    def __parse_rerc(self, rerc):
        m = re.findall('BULLET\s*=>\s*[\'"]\s*(.)\s*[\'"]\s*,', open(rerc, 'r').read())
        if len(m) > 0:
            return m[-1]
        else:
            return '-'

    def __dump_re(self):
        env = os.environ
        env['EDITOR'] = which('cat')
        out, _ = Popen([which('re')], stdout=PIPE).communicate()
        return out.decode()

    def load_work(self):
        out = self.__dump_re()
        if os.path.exists('~/.rerc'):
            bullet = self.__parse_rerc('~/.rerc')
        elif os.path.exists('/etc/rerc'):
            bullet = self.__parse_rerc('/etc/rerc')
        self.work = [line.strip()[1:].strip() for line in out.split('\n') if len(line.strip()) > 0 and line.strip()[0] == bullet]

    def HandleDoNothing(self, obj, name):
        pass

    def HandleEditTask(self, obj, name):
        self.__modify_re(self.__dump_re())

    def HandleFinishedTask(self, obj, name):
        self.request_task()

    def HandleAddTask(self, obj, name):
        self.__modify_re('')

    def __modify_re(self, text):
        self.windows.append(Gtk.Window())
        win = self.windows[-1]
        win.connect("destroy", Gtk.main_quit)
        textview = Gtk.TextView()
        textbuffer = textview.get_buffer()
        textbuffer.set_text(text)
        win.add(textview)
        win.show_all()
        self.load_work()

    def suggest_task(self):
        self.notifications.append(Notify.Notification.new('Tasks', 'This is the next priority task:\n' + summary))
        notify = self.notifications[-1]
        notify.add_action('select', 'Select', self.HandleSelectTask)
        notify.add_action('postpone', 'Delay', self.HandlePostponeTask)
        notify.add_action('addtask', 'Add Task', self.HandleAddTask)
        notify.set_urgency(2)
        notify.set_timeout(0)
        notify.show()

    def request_task(self):
        self.notifications.append(Notify.Notification.new('Tasks', 'What are you working on?'))
        notify = self.notifications[-1]
        notify.add_action('addtask', 'Add Task', self.HandleAddTask);
        notify.set_urgency(2)
        notify.set_timeout(0)
        notify.show()

    def request_work(self, summary):
        self.notifications.append(Notify.Notification.new('Tasks', 'Are you still working on this task?\n' + summary))
        notify = self.notifications[-1]
        notify.add_action('yes', 'Yes', self.HandleDoNothing)
        notify.add_action('view', 'View', self.HandleEditTask)
        notify.add_action('finish', 'Finish', self.HandleFinishedTask)
        notify.set_urgency(2)
        notify.set_timeout(0)
        notify.show()

if __name__ == '__main__':
    tasks = TaskNotify()
    GLib.MainLoop().run()
