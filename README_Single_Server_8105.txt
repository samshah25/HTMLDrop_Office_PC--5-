HTML Drop single-entry-port test bundle

This build serves HTML Drop and proxies dynamic projects through port 8105:
  HTML Drop:          http://127.0.0.1:8105/
  Example project:    http://127.0.0.1:8105/dashboards/test1/

Dynamic project apps still run as internal worker processes on their allocated local ports; browsers should use the /dashboards/<slug>/ URL on port 8105. This avoids exposing separate dashboard ports in links.

Test locally first. This version binds to 127.0.0.1 as a personal-PC test instance. Before office deployment, configure the server to bind to 0.0.0.0 and allow inbound TCP 8105 through the office PC firewall.

Note: reverse-proxy compatibility depends on each app's URL handling. The proxy rewrites common root-relative HTML/CSS/JS asset paths, but apps that hard-code absolute external URLs or use websocket connections may need app-specific adjustments.
