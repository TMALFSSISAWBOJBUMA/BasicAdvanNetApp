from flask import Flask, request, jsonify, Response, send_from_directory
import requests
import pathlib as pl
import os

app = Flask("AdvanNet App Demo")


# from https://stackoverflow.com/a/36601467
@app.route("/proxy/<path:path>", methods=["GET", "PUT", "OPTIONS"])
def proxy_request(
    path,
):
    target = request.headers.get("X-Target-Host", None)
    if target is None:
        return jsonify({"error": "X-Target-Host header is required"}), 400
    res = requests.request(  # ref. https://stackoverflow.com/a/36601467/248616
        method=request.method,
        url=request.url.replace(request.host + "/proxy", f"{target}"),
        headers={
            k: v for k, v in request.headers if k.lower() != "host"
        },  # exclude 'host' header
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
    )

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
    return send_from_directory(pl.Path(__file__).parent, paf)


@app.route("/")
@app.route("/index")
def index():
    return root("index.html")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=os.environ.get("PORT", 8000),
        debug=os.environ.get("DEBUG", False),
    )
