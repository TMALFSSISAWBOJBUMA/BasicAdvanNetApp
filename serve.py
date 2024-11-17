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
import time
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
import re
from datetime import datetime as dt, timezone as tz
import humanize as hm
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    BooleanField,
    DateTimeField,
    IntegrityError,
)
from functools import partial

now = partial(dt.now, tz.utc)
db = SqliteDatabase("advannet_demo.db")


class BaseModel(Model):
    class Meta:
        database = db

    def update_instance(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.save()


class KeonnDevice(BaseModel):
    TYPE_ = "_workstation._tcp.local."
    name = CharField(unique=True, primary_key=True)
    mac = CharField()
    ip = CharField()
    last_link = DateTimeField()
    offline = BooleanField()

    @classmethod
    def name_from_mdns_key(cls, mdns_key: str) -> str:
        return re.compile("(?P<name>.*) \\[(?P<mac>.*)\\].*").match(mdns_key)["name"]

    def mdns_update(self, zc: Zeroconf):
        data = self.ServiceInfo_to_dict(
            zc.get_service_info(self.TYPE_, self.to_mdns_name(), 1000)
        )
        self.update_instance(**data)

    @classmethod
    def ServiceInfo_to_dict(
        cls, info: ServiceInfo, name: str | None = None
    ) -> dict[str, str]:
        ret = {"offline": info is None}
        if name:
            parsed = re.compile("(?P<name>.*) \\[(?P<mac>.*)\\].*").match(name)
            ret.update({"name": parsed["name"], "mac": parsed["mac"]})
        if ret["offline"]:
            return ret
        parsed = re.compile("(?P<name>.*) \\[(?P<mac>.*)\\].*").match(info.name)
        ret.update(
            {
                "name": parsed["name"],
                "mac": parsed["mac"],
                "last_link": now(),
                "ip": info.parsed_addresses()[0],
            }
        )
        return ret

    def to_mdns_name(self) -> str:
        return f"{self.name} [{self.mac}].{self.TYPE_}"


class KeonnFinder:
    __last_check = 0
    CHECK_PERIOD = 10
    TYPE_ = KeonnDevice.TYPE_

    def __init__(self) -> None:
        self.__zc = Zeroconf(unicast=True)
        self.__browser = ServiceBrowser(
            self.__zc,
            self.TYPE_,
            listener=self,
            delay=1000,
        )

    def restart_browser(self):
        print("Restarting ServiceBrowser")
        self.__browser.cancel()
        self.__browser = ServiceBrowser(
            self.__zc,
            self.TYPE_,
            listener=self,
            delay=1000,
        )

    def get_devices(self):
        if time.time() - self.__last_check > self.CHECK_PERIOD:
            self.__last_check = time.time()
            for device in KeonnDevice.select():
                device: KeonnDevice
                device.mdns_update(self.__zc)
                yield device
        else:
            for device in KeonnDevice.select():
                yield device

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"ServiceBrowser updated {name}")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"ServiceBrowser removed {name}")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        zc_info = zc.get_service_info(type_, name)
        if zc_info is None:
            return
        try:
            data = KeonnDevice.ServiceInfo_to_dict(zc_info)
            dev, created = KeonnDevice.get_or_create(
                name=KeonnDevice.name_from_mdns_key(name), defaults=data
            )
            if not created:
                dev: KeonnDevice
                dev.update_instance(**data)
        except IntegrityError:
            pass
        print(f"ServiceBrowser added {name}")

    def close(self):
        self.__zc.close()


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
    if request.args.get("restart", None) is not None:
        app.config["KEONN_FINDER"].restart_browser()

    def time_diff(str_date: str | dt) -> str:
        return hm.naturaltime(
            isinstance(str_date, str) and dt.fromisoformat(str_date) or str_date
        )

    links_html = render_template(
        "links.html.j2",
        devices=app.config["KEONN_FINDER"].get_devices(),
        time_diff=time_diff,
    )
    if request.args.get("links", None) is None:
        return render_template("scan.html.j2", links=links_html)
    return links_html


if __name__ == "__main__":
    KeonnDevice.create_table(safe=True)
    listener = KeonnFinder()
    try:
        app.config["KEONN_FINDER"] = listener
        app.run(
            host="0.0.0.0",
            port=os.environ.get("PORT", 8000),
            debug=os.environ.get("DEBUG", False),
        )
    finally:
        listener.close()
