import time

####################
# Session Handling:
# we currently lock the session when one event is e.g. reading from disk
# subsequent requests have to wait until the previous request is done.
# maybe a wait list is also necessary here, to be able to have each request
# answer in the same order as they came in...
##################

class SessionManager(object):
    def __init__(self):
        self.sessions = {}
        self.locked_sessions = []

    def get_session(self, sid, lock=True):
        if sid not in self.sessions:
            self.sessions[sid] = {}

        class _session_context_manager(object):
            def __init__(self, _sid, lock_session, _session_manager):
                self.sid = _sid
                self.sm = _session_manager
                self.session = self.sm.sessions[_sid]
                self.lock = lock_session

            def __enter__(self):
                while self.sid in self.sm.locked_sessions:
                    time.sleep(0.001)
                if self.lock:
                    self.sm.locked_sessions.append(sid)
                return self.session

            def __exit__(self, _, value, traceback):
                if self.lock:
                    del self.sm.locked_sessions[self.sm.locked_sessions.index(sid)]

        return _session_context_manager(sid, lock, self)

    def has_sid(self, sid):
        return sid in self.sessions.keys()

    def reset_sessions(self):
        self.sessions = {}
        self.locked_sessions = []


session_manager = SessionManager()
