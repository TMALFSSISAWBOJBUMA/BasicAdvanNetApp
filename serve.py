from flask import (
    Flask,
    request,
    jsonify,
    Response,
    send_from_directory,
    abort,
    render_template,
    redirect,
)
import requests
from requests.exceptions import ConnectionError
from requests.auth import HTTPDigestAuth
import pathlib as pl
import os
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


class MyListener(ServiceListener):
    devices: dict[str:str] = {}

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        self.devices[name] = info.parsed_addresses()[0]
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")
        del self.devices[name]

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added")
        self.devices[name] = info.parsed_addresses()[0]


app = Flask("AdvanNet App Demo")


PROXY_URL = "/keonn_proxy"


# from https://stackoverflow.com/a/36601467
@app.route(f"{PROXY_URL}/<path:path>", methods=["GET", "PUT", "OPTIONS"])
def proxy_request(
    path,
):
    target = request.headers.get("X-Target-Host", None)
    if target is None:
        return jsonify({"error": "X-Target-Host header is required"}), 400
    try:
        res = requests.request(  # ref. https://stackoverflow.com/a/36601467/248616
            method=request.method,
            url=request.url.replace(request.host + PROXY_URL, f"{target}"),
            headers={
                k: v for k, v in request.headers if k.lower() != "host"
            },  # exclude 'host' header
            data=request.get_data(),
            cookies=request.cookies,
            timeout=2,
            auth=HTTPDigestAuth("admin", "admin"),
        )
    except ConnectionError:
        abort(502)

    # region exlcude some keys in :res response
    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
        "hop-by-hop headers",
    ]
    headers = [
        (k, v) for k, v in res.raw.headers.items() if k.lower() not in excluded_headers
    ]
    # endregion exlcude some keys in :res response

    response = Response(res.content, res.status_code, headers)
    return response


@app.route("/<path:paf>")
def root(paf):
    return send_from_directory(pl.Path(__file__).parent / "static", paf)


@app.route("/connect")
def connect():
    return root("index.html")


@app.route("/")
def index():
    return redirect("/scan")


@app.route("/scan")
def devices():
    links_html = render_template(
        "links.html.j2", devices=app.config["KEONN_FINDER"].devices
    )
    if request.args.get("links", None) is None:
        return render_template("scan.html.j2", links=links_html)
    return links_html


if __name__ == "__main__":
    zeroconf = Zeroconf(unicast=True)
    listener = MyListener()
    browser = ServiceBrowser(zeroconf, "_workstation._tcp.local.", listener)
    try:
        app.config["KEONN_FINDER"] = listener
        app.run(
            host="0.0.0.0",
            port=os.environ.get("PORT", 8000),
            debug=os.environ.get("DEBUG", False),
        )
    finally:
        zeroconf.close()
