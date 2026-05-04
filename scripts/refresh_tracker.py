#!/usr/bin/env python3
"""Weekly refresh of vehicle-tracker-v2.html with live Snowflake data."""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import snowflake.connector


def connect():
    private_key = os.environ.get("SNOWFLAKE_PRIVATE_KEY")
    if private_key:
        import base64
        from cryptography.hazmat.primitives import serialization
        key_bytes = base64.b64decode(private_key)
        pk = serialization.load_pem_private_key(key_bytes, password=None)
        pk_bytes = pk.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            private_key=pk_bytes,
            role=os.environ.get("SNOWFLAKE_ROLE", "FULFILLMENT_ANALYTICS"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "FULFILLMENT_ANALYTICS"),
        )
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "FULFILLMENT_ANALYTICS"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "FULFILLMENT_ANALYTICS"),
    )


def query_moves(cur, start_date):
    cur.execute(f"""
        SELECT DATE_TRUNC('WEEK', LAST_READ_UTC)::DATE AS week_start,
               LOCATION_CODE, LOCATION,
               COUNT(DISTINCT VIN) AS units_moved
        FROM INVENTORY.VEHICLE_QUALITY.VW_VEHICLE_LOCATION_HISTORY
        WHERE LOCATION_CHANGED_FLAG = TRUE
          AND LAST_READ_UTC >= '{start_date}'
          AND LOCATION_CODE IS NOT NULL
          AND LOCATION_CODE NOT IN ('OffSite','InTransit','Unknown')
        GROUP BY 1, 2, 3
        ORDER BY week_start, units_moved DESC
    """)
    return cur.fetchall()


def query_recon(cur, start_date):
    cur.execute(f"""
        SELECT REPAIR_WEEK_START AS week_start,
               LOCATION_CODE, LOCATION_NAME,
               COUNT(DISTINCT STOCK_NUMBER) AS units_reconditioned
        FROM INVENTORY.VEHICLE_QUALITY.FACT_REPAIR_CYCLE
        WHERE REPAIR_WEEK_START >= '{start_date}'
          AND END_DATETIME_UTC IS NOT NULL
        GROUP BY 1, 2, 3
        ORDER BY week_start, units_reconditioned DESC
    """)
    return cur.fetchall()


def query_sales(cur, start_date):
    cur.execute(f"""
        SELECT DATE_TRUNC('WEEK', fs.SALE_EFFECTIVE_DATE)::DATE AS week_start,
               dv.VEHICLE_LOCATION_LOCATION_CODE AS location_code,
               dv.VEHICLE_LOCATION_LOCATION_NAME AS location_name,
               COUNT(DISTINCT dv.STOCK_NUMBER) AS units_sold
        FROM SHARED.DW.FACT_SALE fs
        JOIN SHARED.DW.DIM_VEHICLE dv ON fs.VEHICLE_SK = dv.VEHICLE_SK
        WHERE fs.SALE_EFFECTIVE_DATE >= '{start_date}'
          AND fs.IS_PURCHASE_COMPLETED = TRUE
          AND dv.VEHICLE_LOCATION_LOCATION_CODE IS NOT NULL
        GROUP BY 1, 2, 3
        ORDER BY week_start, units_sold DESC
    """)
    return cur.fetchall()


def query_vehicle_weekly(cur, start_date):
    cur.execute(f"""
        SELECT DATE_TRUNC('WEEK', fs.SALE_EFFECTIVE_DATE)::DATE AS week_start,
               dv.MAKE || ' ' || dv.MODEL AS vehicle,
               dv.BODY_STYLE AS body,
               dv.YEAR AS top_year,
               COUNT(DISTINCT dv.STOCK_NUMBER) AS units_sold
        FROM SHARED.DW.FACT_SALE fs
        JOIN SHARED.DW.DIM_VEHICLE dv ON fs.VEHICLE_SK = dv.VEHICLE_SK
        WHERE fs.SALE_EFFECTIVE_DATE >= '{start_date}'
          AND fs.IS_PURCHASE_COMPLETED = TRUE
        GROUP BY 1, 2, 3, 4
        QUALIFY ROW_NUMBER() OVER (PARTITION BY week_start ORDER BY units_sold DESC) <= 25
        ORDER BY week_start DESC, units_sold DESC
    """)
    return cur.fetchall()


def query_vehicle_locations(cur, start_date):
    cur.execute(f"""
        WITH top_vehicles AS (
          SELECT DATE_TRUNC('WEEK', fs.SALE_EFFECTIVE_DATE)::DATE AS week_start,
                 dv.MAKE || ' ' || dv.MODEL AS vehicle,
                 dv.VEHICLE_LOCATION_LOCATION_CODE AS loc_code,
                 dv.VEHICLE_LOCATION_LOCATION_NAME AS loc_name,
                 COUNT(DISTINCT dv.STOCK_NUMBER) AS units
          FROM SHARED.DW.FACT_SALE fs
          JOIN SHARED.DW.DIM_VEHICLE dv ON fs.VEHICLE_SK = dv.VEHICLE_SK
          WHERE fs.SALE_EFFECTIVE_DATE >= '{start_date}'
            AND fs.IS_PURCHASE_COMPLETED = TRUE
            AND dv.VEHICLE_LOCATION_LOCATION_CODE IS NOT NULL
          GROUP BY 1,2,3,4
        )
        SELECT week_start, vehicle, loc_code, loc_name, units
        FROM top_vehicles
        WHERE vehicle IN (
          SELECT vehicle FROM (
            SELECT vehicle, SUM(units) as t FROM top_vehicles GROUP BY vehicle ORDER BY t DESC LIMIT 15
          )
        )
        QUALIFY ROW_NUMBER() OVER (PARTITION BY week_start, vehicle ORDER BY units DESC) <= 5
        ORDER BY week_start DESC, vehicle, units DESC
    """)
    return cur.fetchall()


def query_gps(cur):
    cur.execute("""
        SELECT LOCATION_CODE, ROUND(AVG(LATITUDE),2) as lat, ROUND(AVG(LONGITUDE),2) as lng
        FROM INVENTORY.VEHICLE_QUALITY.VW_VEHICLE_LOCATION_HISTORY
        WHERE LAST_READ_UTC >= DATEADD(day, -30, CURRENT_TIMESTAMP())
          AND LATITUDE IS NOT NULL
          AND LOCATION_CODE IS NOT NULL
        GROUP BY LOCATION_CODE
        ORDER BY LOCATION_CODE
    """)
    return cur.fetchall()


def rows_to_js(rows, var_name):
    by_week = {}
    for r in rows:
        week = str(r[0])
        code = r[1]
        name = r[2] or code
        value = int(r[3])
        by_week.setdefault(week, []).append((code, name, value))

    weeks = sorted(by_week.keys())
    parts = []
    for w in weeks:
        entries = ",".join(f'["{e[0]}","{e[1]}",{e[2]}]' for e in by_week[w])
        parts.append(f'...p("{w}",[{entries}])')
    return f"const {var_name}=[\n" + ",\n".join(parts) + "\n];"


def vehicle_weekly_to_js(rows):
    by_week = {}
    for r in rows:
        week = str(r[0])
        vehicle = r[1]
        body = r[2] or "Unknown"
        units = int(r[4])
        by_week.setdefault(week, []).append((vehicle, body, units))

    weeks = sorted(by_week.keys())
    parts = []
    for w in weeks:
        entries = ",".join(f'["{e[0]}","{e[1]}",{e[2]}]' for e in by_week[w])
        parts.append(f'...p("{w}",[{entries}])')
    return f"const VEHICLE_WEEKLY=[\n" + ",\n".join(parts) + "\n];"


def vehicle_locations_to_js(rows):
    by_week = {}
    for r in rows:
        w, veh, lc, ln, u = str(r[0]), r[1], r[2], r[3], int(r[4])
        by_week.setdefault(w, {}).setdefault(veh, []).append([lc, ln, u])

    weeks = sorted(by_week.keys())
    lines = []
    for w in weeks:
        vehs = []
        for v, locs in by_week[w].items():
            total = sum(l[2] for l in locs)
            loc_str = ",".join(f'["{l[0]}","{l[1]}",{l[2]}]' for l in locs)
            vehs.append((total, v, loc_str))
        vehs.sort(key=lambda x: -x[0])
        entries = ",".join(f'{{v:"{v}",t:{t},l:[{ls}]}}' for t, v, ls in vehs)
        lines.append(f'{{w:"{w}",d:[{entries}]}}')
    return "const VEH_LOC_DATA=[\n" + ",\n".join(lines) + "\n];"


def gps_to_js(rows):
    entries = ",".join(f'"{r[0]}":[{float(r[1]):.2f},{float(r[2]):.2f}]' for r in rows if r[1] and r[2])
    return f"const GPS={{{entries}}};"


def replace_js_var(html, var_name, new_js):
    pattern = f"const {var_name}="
    start = html.index(pattern)
    end = html.index("];", start) + 2
    return html[:start] + new_js + html[end:]


def replace_js_obj_var(html, var_name, new_js):
    pattern = f"const {var_name}="
    start = html.index(pattern)
    end = html.index("};", start) + 2
    return html[:start] + new_js + html[end:]


def update_week_dropdown(html, all_weeks):
    weeks = sorted(all_weeks, reverse=True)
    options = []
    for w in weeks:
        d = datetime.strptime(w, "%Y-%m-%d")
        end = d + timedelta(days=6)
        label = f'{d.strftime("%b")} {d.day} - {end.strftime("%b")} {end.day}, {end.year}'
        options.append(f'                <option value="{w}">{label}</option>')
    options_str = "\n".join(options)

    opt_start = html.index('<select id="week-select">') + len('<select id="week-select">') + 1
    opt_end = html.index("</select>", opt_start)
    return html[:opt_start] + options_str + "\n            " + html[opt_end:]


def main():
    start_date = "2026-01-05"
    print(f"Connecting to Snowflake (account: {os.environ.get('SNOWFLAKE_ACCOUNT', '?')})...")
    conn = connect()
    cur = conn.cursor()

    print("Querying vehicle moves...")
    moves = query_moves(cur, start_date)
    print(f"  -> {len(moves)} rows")

    print("Querying reconditioning cycles...")
    recon = query_recon(cur, start_date)
    print(f"  -> {len(recon)} rows")

    print("Querying sales...")
    sales = query_sales(cur, start_date)
    print(f"  -> {len(sales)} rows")

    print("Querying vehicle weekly rankings...")
    veh_weekly = query_vehicle_weekly(cur, start_date)
    print(f"  -> {len(veh_weekly)} rows")

    print("Querying vehicle-location drill-down...")
    veh_locs = query_vehicle_locations(cur, start_date)
    print(f"  -> {len(veh_locs)} rows")

    print("Querying GPS coordinates...")
    gps = query_gps(cur)
    print(f"  -> {len(gps)} locations")

    cur.close()
    conn.close()

    print("Updating HTML...")
    html_path = Path(__file__).parent.parent / "vehicle-tracker-v2.html"
    html = html_path.read_text(encoding="utf-8")

    all_weeks = sorted({str(r[0]) for r in moves + recon + sales})

    html = replace_js_var(html, "MOVES_DATA", rows_to_js(moves, "MOVES_DATA"))
    html = replace_js_var(html, "RECON_DATA", rows_to_js(recon, "RECON_DATA"))
    html = replace_js_var(html, "SALES_DATA", rows_to_js(sales, "SALES_DATA"))
    html = replace_js_var(html, "VEHICLE_WEEKLY", vehicle_weekly_to_js(veh_weekly))
    html = replace_js_var(html, "VEH_LOC_DATA", vehicle_locations_to_js(veh_locs))
    html = replace_js_obj_var(html, "GPS", gps_to_js(gps))

    weeks_js = "const WEEKS=" + json.dumps(sorted(all_weeks)) + ";"
    ws = html.index("const WEEKS=")
    we = html.index(";", ws) + 1
    html = html[:ws] + weeks_js + html[we:]

    html = update_week_dropdown(html, all_weeks)

    html_path.write_text(html, encoding="utf-8")
    print(f"Written to {html_path} ({len(html):,} bytes)")
    print(f"Weeks: {all_weeks[0]} to {all_weeks[-1]} ({len(all_weeks)} weeks)")


if __name__ == "__main__":
    main()
