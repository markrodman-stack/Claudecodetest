#!/usr/bin/env python3
"""Weekly refresh of vehicle-tracker-v2.html with live Snowflake data."""

import json
import os
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
        QUALIFY ROW_NUMBER() OVER (PARTITION BY week_start ORDER BY units_moved DESC) <= 30
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
        QUALIFY ROW_NUMBER() OVER (PARTITION BY week_start ORDER BY units_reconditioned DESC) <= 30
        ORDER BY week_start, units_reconditioned DESC
    """)
    return cur.fetchall()


def query_sales(cur, start_date):
    cur.execute(f"""
        SELECT DATE_TRUNC('WEEK', fs.SALE_EFFECTIVE_DATE)::DATE AS week_start,
               dv.PRODUCTION_LOCATION AS location_code,
               dv.PRODUCTION_LOCATION_CITY_STATE AS location_name,
               COUNT(DISTINCT dv.STOCK_NUMBER) AS units_sold
        FROM SHARED.DW.FACT_SALE fs
        JOIN SHARED.DW.DIM_VEHICLE dv ON fs.VEHICLE_SK = dv.VEHICLE_SK
        WHERE fs.SALE_EFFECTIVE_DATE >= '{start_date}'
          AND fs.IS_PURCHASE_COMPLETED = TRUE
          AND dv.PRODUCTION_LOCATION IS NOT NULL
        GROUP BY 1, 2, 3
        QUALIFY ROW_NUMBER() OVER (PARTITION BY week_start ORDER BY units_sold DESC) <= 30
        ORDER BY week_start, units_sold DESC
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


def build_weeks_js(all_rows):
    weeks = sorted({str(r[0]) for r in all_rows})
    return "const WEEKS=" + json.dumps(weeks) + ";"


def build_week_options(all_rows):
    weeks = sorted({str(r[0]) for r in all_rows}, reverse=True)
    options = []
    for w in weeks:
        d = datetime.strptime(w, "%Y-%m-%d")
        end = d + timedelta(days=6)
        label = f'{d.strftime("%b %-d")} - {end.strftime("%b %-d, %Y")}'
        options.append(f'                <option value="{w}">{label}</option>')
    return "\n".join(options)


def generate_html(moves, recon, sales):
    template_path = Path(__file__).parent.parent / "vehicle-tracker-v2.html"
    template = template_path.read_text(encoding="utf-8")

    split_marker = "<script>"
    top_html = template.split(split_marker)[0]

    all_rows = moves + recon + sales
    week_options = build_week_options(all_rows)

    top_html_lines = top_html.split("\n")
    new_lines = []
    in_week_select = False
    for line in top_html_lines:
        if 'id="week-select"' in line:
            in_week_select = True
            new_lines.append(line)
            continue
        if in_week_select:
            if "</select>" in line:
                new_lines.append(week_options)
                new_lines.append(line)
                in_week_select = False
            continue
        new_lines.append(line)

    top_html = "\n".join(new_lines)

    weeks_js = build_weeks_js(all_rows)
    moves_js = rows_to_js(moves, "MOVES_DATA")
    recon_js = rows_to_js(recon, "RECON_DATA")
    sales_js = rows_to_js(sales, "SALES_DATA")

    js_start = template.split(split_marker)[1]
    static_js_start = js_start.find("function fmt(")
    static_js = js_start[static_js_start:] if static_js_start != -1 else ""

    gps_block = """const GPS={
"CON-IC":[35.37,-80.63],"NNJ-IC":[40.55,-74.58],"DEL-IC":[40.04,-74.93],"ELY-IC":[41.41,-82.16],
"HNS-IC":[28.08,-81.60],"IND-IC":[39.82,-85.92],"UNI-IC":[41.46,-87.73],"HEA-IC":[40.00,-82.47],
"CHE-IC":[37.32,-77.40],"BLM-IC":[32.85,-97.34],"PHX-IC":[33.44,-112.26],"LCA-IC":[34.02,-117.38],
"OKC-IC":[35.41,-97.63],"HST-IC":[29.94,-95.49],"ROC-IC":[38.83,-121.31],"ATG-IC":[33.54,-84.55],
"DAL-IC":[32.62,-96.74],"BMA-IC":[42.26,-71.41],"TRE-IC":[39.46,-84.47],"WME-IC":[35.18,-90.21],
"KCM-IC":[38.84,-94.54],"WND-IC":[33.99,-83.75],"WND-OL":[33.99,-83.75],"BES-IC":[33.37,-86.94],
"SAA-IC":[29.30,-98.39],"BNY-IC":[43.00,-78.53],"AIN-IC":[39.73,-86.35],"CAZ-IC":[33.31,-111.96],
"TCA-IC":[37.73,-121.54],"NTN-IC":[36.16,-86.78],"TOO-IC":[40.54,-112.35],"LNV-IC":[36.21,-115.22],
"POS-IC":[45.55,-122.42],"SDC-IC":[32.72,-117.16],"SWA-IC":[47.31,-122.23],"EOR-IC":[44.05,-123.09],
"LNY-IC":[40.84,-72.88],"CCO-IC":[38.71,-104.75],"PAZ-HB":[33.43,-112.10],"MOB-LH":[30.69,-88.04],
"WFM-HB":[43.01,-83.69],"MOR-LH":[34.99,-106.05],"BLH-HB":[39.27,-76.56],"MMC-HB":[44.98,-93.27]
};"""

    data_block = f"{gps_block}\n{weeks_js}\nfunction p(w,entries){{return entries.map(e=>({{week:w,code:e[0],name:e[1],value:e[2]}}))}}\n{moves_js}\n{recon_js}\n{sales_js}"

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    updated_comment = f"// Auto-refreshed from Snowflake on {now}\n"

    return f"{top_html}<script>\n{updated_comment}{data_block}\n{static_js}"


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

    cur.close()
    conn.close()

    print("Generating HTML...")
    html = generate_html(moves, recon, sales)

    out_path = Path(__file__).parent.parent / "vehicle-tracker-v2.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Written to {out_path} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
