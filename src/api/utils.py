from flask import jsonify, url_for


class APIException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['status'] = 'error'          # el front espera { status: "error", message }
        rv['message'] = self.message
        return rv


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


def generate_sitemap(app):
    links = []
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            if "/admin/" not in url:
                links.append(url)
    links_html = "".join(["<li><a href='" + y + "'>" + y + "</a></li>" for y in sorted(links)])
    return """
        <div style="font-family: sans-serif; max-width: 640px; margin: 40px auto;">
        <h1>FinFluent API</h1>
        <p>Backend en marcha. El front corre en el puerto 3000 (<code>npm run dev</code>).</p>
        <ul style="text-align: left;">""" + links_html + "</ul></div>"
