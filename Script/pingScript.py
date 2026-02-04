#!/usr/bin/env python3
import time
import csv
import telnetlib
from datetime import datetime
from ping3 import ping  
import re
import statistics


# -----------------------------
# CONFIGURATION (EDIT THESE)
# -----------------------------
PING_TARGET = "1.1.1.1"
TELNET_IP = "192.168.2.2"
TELNET_PORT = 23
TELNET_USER = "admin"
TELNET_PASS = "Aa111111"

TRACK_INTERFACE = "GigabitEthernet0/0"

# The real physical IP that will be removed/added
MASTER_IP = "192.168.1.254"
MASTER_MASK = "255.255.255.0"

TEST_COUNT = 500
PING_INTERVAL = 0.01
SHUTDOWN_DELAY = 2.0
MAX_SHUTDOWN_WAIT = 20.0
EXPERIMENT_SLEEP = 15.0

SUMMARY_CSV = "vrrp_results.csv"

# -----------------------------
# Telnet functions
# -----------------------------
def telnet_connect(ip, port, user, password, timeout=5):
    tn = telnetlib.Telnet(ip, port, timeout)
    tn.read_until(b"Username:", timeout)
    tn.write(user.encode('ascii') + b"\n")
    tn.read_until(b"Password:", timeout)
    tn.write(password.encode('ascii') + b"\n")
    tn.read_until(b"#", timeout)
    return tn

def telnet_cmd(tn, cmd, wait=0.3):
    tn.write(cmd.encode('ascii') + b"\n")
    time.sleep(wait)
    return tn.read_very_eager().decode(errors="ignore")

# REMOVE IP ADDRESS
def remove_ip(tn, ifname, ip, mask):
    cmds = f"conf t\ninterface {ifname}\nno ip address {ip} {mask}\nend\n"
    tn.write(cmds.encode('ascii') + b"\n")
    tn.read_until(b"#", timeout=2)

# ADD IP ADDRESS
def add_ip(tn, ifname, ip, mask):
    cmds = f"conf t\ninterface {ifname}\nip address {ip} {mask}\nend\n"
    tn.write(cmds.encode('ascii') + b"\n")
    tn.read_until(b"#", timeout=2)

# -----------------------------
# Get CPU usage
# -----------------------------
def get_cpu_usage(tn):
    telnet_cmd(tn,"end")
    out = telnet_cmd(tn, "show processes cpu | include CPU")
    
    # Example:
    # CPU utilization for five seconds: 2%/0%; one minute: 4%; five minutes: 11%
    m = re.search(r"five seconds:\s*(\d+)%", out)
    if m:
        return float(m.group(1))
    
    return None

# -----------------------------
# Ping once using ping3
# -----------------------------
def ping_once(target_ip, timeout=1):
    try:
        rtt = ping(target_ip, timeout=timeout)
        if rtt is not None:
            return rtt * 1000  # seconds → ms
        return None
    except:
        return None

# -----------------------------
# RUN A SINGLE EXPERIMENT
# -----------------------------
def run_experiment(exp_num):
    print(f"\n=== Starting Experiment {exp_num} ===")
    start_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        tn = telnet_connect(TELNET_IP, TELNET_PORT, TELNET_USER, TELNET_PASS)
    except Exception as e:
        print(f"[ERROR] Telnet connect failed: {e}")
        return None

    # ALWAYS restore IP before test
    add_ip(tn, TRACK_INTERFACE, MASTER_IP, MASTER_MASK)


    # Record CPU before failover
    cpu_before = get_cpu_usage(tn)
    # print(f"CPU before failover: {cpu_before}%")


    ping_log = []
    experiment_start = time.time()

    fail_start_ts = None
    fail_end_ts = None
    shutdown_issued = False
    restore_issued = False
    shutdown_time = None

    while True:
        now = time.time()
        rel = round(now - experiment_start, 3)
        latency = ping_once(PING_TARGET)

        ping_log.append([rel, latency])

        # outage detection
        if latency is None:
            if fail_start_ts is None:
                fail_start_ts = now
                fail_test = round(now - experiment_start, 3)
                # print(f"[{fail_test}s] Ping outage detected")
        else:
            if fail_start_ts is not None and fail_end_ts is None:
                fail_end_ts = now

        # REMOVE IP instead of shutdown
        if (not shutdown_issued) and (now - experiment_start >= SHUTDOWN_DELAY):
            # print(f"[{rel}s] TELNET remove IP from {TRACK_INTERFACE}")
            remove_ip(tn, TRACK_INTERFACE, MASTER_IP, MASTER_MASK)
            shutdown_issued = True
            shutdown_time = now

# RESTORE IP when ping recovers
        if shutdown_issued and not restore_issued:
            if (time.time() - shutdown_time) >= MAX_SHUTDOWN_WAIT:
                # print("Safety restore triggered")
                add_ip(tn, TRACK_INTERFACE, MASTER_IP, MASTER_MASK)
                restore_issued = True
                cpu_after = 0
                break
            else:
                if fail_start_ts and fail_end_ts:
                    # print(f"[{rel}s] Ping recovered — restoring IP")
                    add_ip(tn, TRACK_INTERFACE, MASTER_IP, MASTER_MASK)
                    restore_issued = True
                    time.sleep(2)

                    # Record post-failover CPU
                    cpu_after = get_cpu_usage(tn)
                    # print(f"CPU after: {cpu_after}%")
                    break


        time.sleep(PING_INTERVAL)

    tn.close()

    # compute metrics
    total = len(ping_log)
    success = sum(1 for _, p in ping_log if p is not None)
    loss = total - success
    pkt_loss_pct = loss / total * 100 if total else None

    latencies = [p for _, p in ping_log if p is not None]
    avg_lat = sum(latencies) / len(latencies) if latencies else None
    min_lat = min(latencies) if latencies else None
    max_lat = max(latencies) if latencies else None


    # Standard deviation (jitter)
    jitter = round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0.0
    # Median latency
    median_lat = round(statistics.median(latencies), 3) if latencies else None
    # Percentiles
    lat_sorted = sorted(latencies)
    p95 = round(lat_sorted[int(0.95 * len(lat_sorted)) - 1], 3) if latencies else None
    p99 = round(lat_sorted[int(0.99 * len(lat_sorted)) - 1], 3) if latencies else None

    fail_start_rel = round(fail_start_ts - experiment_start, 3) if fail_start_ts else None
    fail_end_rel = round(fail_end_ts - experiment_start, 3) if fail_end_ts else None
    failover_duration = round(fail_end_ts - fail_start_ts, 4) if (fail_start_ts and fail_end_ts) else None
    print(failover_duration)
    return [
        exp_num, start_str, PING_TARGET, TRACK_INTERFACE,
        fail_start_rel, fail_end_rel, failover_duration,
        failover_duration, total, success, loss, pkt_loss_pct,
        avg_lat, min_lat, max_lat, cpu_before , cpu_after , jitter, median_lat, p95, p99
    ]

# -----------------------------
# MAIN
# -----------------------------
def main():
    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "Experiment", "Date", "Ping_Target", "Tracked_Interface",
            "Fail_Start_Time", "Fail_End_Time",
            "Failover_Duration_sec", "Ping_Loss_Duration_sec",
            "Total_Pings", "Successful_Pings", "Lost_Pings",
            "Packet_Loss_Percent", "Avg_Latency_ms",
            "Min_Latency_ms", "Max_Latency_ms", "CPU_Before", "CPU_After", "Jitter_ms", "Median_Latency_ms", "Latency_95th_ms", "Latency_99th_ms"

        ])

    for i in range(1, TEST_COUNT + 1):
        row = run_experiment(i)
        if row:
            with open(SUMMARY_CSV, "a", newline="") as f:
                csv.writer(f).writerow(row)
        time.sleep(EXPERIMENT_SLEEP)

    print("Finished all experiments.")

if __name__ == "__main__":
    main()