#!/usr/bin/python3
from gi import require_version
require_version('Notify', '0.7')
require_version('Gtk', '3.0')
from gi.repository import Notify, GLib, Gtk
from subprocess import Popen, PIPE
from time import sleep
import os, re
from shutil import which
from icalendar import Todo

class Tasks:
    def __init__(self):
        self.tasks = []
        self.task_file = os.path.expanduser('~/.local/share/evolution/tasks/system/tasks.ics')

    def __load_tasks(self, task_file):
        if os.path.exists(task_file):
            with open(task_file, 'r') as tf:
                data = Todo.from_ical(tf.read())
                self.tasks = [item for item in data.walk('VTODO') if (('PERCENT-COMPLETE' in item.keys() and item['PERCENT-COMPLETE'] != 100) or 'PERCENT-COMPLETE' not in item.keys()) and 'PRIORITY' in item.keys()]

    def highest_priority(self):
        self.__load_tasks(self.task_file)
        if len(self.tasks) == 0:
            return None
        item = self.tasks[0]
        for i in self.tasks[1:]:
            if i['PRIORITY'] > item['PRIORITY']:
                item = i
        return item['SUMMARY']

class TaskNotify:
    def __init__(self):
        Notify.init('Task Tracker')
        self.notifications = []
        self.windows = []
        self.work = []
        self.tasks = Tasks()
        self.prompt_timeout()
        GLib.timeout_add(1200*1000, self.prompt_timeout)

    def prompt_timeout(self):
        self.load_work()
        next_task = self.tasks.highest_priority()
        if len(self.work) > 0:
            self.request_work(self.work[0])
        elif next_task:
            self.suggest_task(next_task)
        else:
            self.request_task()
        return True

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
        return '\n'.join(out.decode().split('\n')[1:])

    def load_work(self):
        out = self.__dump_re()
        if os.path.exists('~/.rerc'):
            bullet = self.__parse_rerc('~/.rerc')
        elif os.path.exists('/etc/rerc'):
            bullet = self.__parse_rerc('/etc/rerc')
        self.work = [line.strip()[1:].strip() for line in out.split('\n') if len(line.strip()) > 0 and line.strip()[0] == bullet]

    def HandleDoNothing(self, obj, name):
        self.notifications.pop()

    def HandleEditTask(self, obj, name):
        self.notifications.pop()
        self.__modify_re('Modify', self.__dump_re())

    def HandleFinishedTask(self, obj, name):
        self.notifications.pop()
        next_task = self.tasks.highest_priority()
        if next_task:
            self.suggest_task(next_task)
        else:
            self.request_task()

    def HandleAddTask(self, obj, name):
        self.notifications.pop()
        self.__modify_re('Add', '', append=True)

    def HandleSelectTask(self, obj, name, summary):
        self.notifications.pop()
        self.__modify_re('Add', summary, append=True)

    def __save_re(self, obj, append, textbuffer):
        s = textbuffer.get_start_iter()
        e = textbuffer.get_end_iter()
        text = textbuffer.get_text(s, e, True)
        if append:
            text = text.replace('\n', ' ').strip()
            Popen([which('re'), text], stdout=PIPE, stderr=PIPE).wait()
        else:
            # Get the filename
            env = os.environ
            env['EDITOR'] = which('echo')
            out, _ = Popen([which('re')], env=env, stdout=PIPE, stderr=PIPE).communicate()
            fname = out.decode().strip().split('\n')[-1].strip()
            with open(fname, 'w') as f:
                f.write(text)

    def __modify_re(self, title, text, append=False):
        self.windows.append(Gtk.Window())
        win = self.windows[-1]
        win.set_default_size(500, 350)
        win.connect("destroy", Gtk.main_quit)

        # Header
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = 'Task Tracker - %s' % title
        win.set_titlebar(hb)
        save = Gtk.Button()
        save.set_label('Save')
        hb.pack_end(save)

        # Main Document
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)
        win.add(scrolledwindow)
        textview = Gtk.TextView()
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textbuffer = textview.get_buffer()
        textbuffer.set_text(text)
        save.connect('clicked', self.__save_re, append, textbuffer)
        scrolledwindow.add(textview)
        win.show_all()
        self.load_work()

    def suggest_task(self, summary):
        self.notifications.append(Notify.Notification.new('Tasks', 'This is the next priority task:\n' + summary))
        notify = self.notifications[-1]
        notify.add_action('select', 'Select', self.HandleSelectTask, summary)
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
