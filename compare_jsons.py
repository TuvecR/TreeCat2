import json
import pandas as pd
from datetime import datetime
import re
import csv

input_json = "j_mcxv2uey69cq92f9i.json"
campaign_csv = "campaign_tracking.csv"
output_json = "2_Doc_Completed.json"
output_excel = "2_Doc_Completed.xlsx"

def normalize_youtube_url(url):
    if not isinstance(url, str):
        return ""
    return re.sub(r"/(about|videos|community|featured|shorts|playlists|streams|posts)?/?$", "", url.split("?")[0]).rstrip("/")

def extract_url(entry):
    return normalize_youtube_url(
        entry.get("url") or
        entry.get("channel_url") or
        entry.get("youtube") or
        ""
    )

def extract_channel_name(entry):
    return (
        entry.get("channel") or
        entry.get("channel_name") or
        entry.get("Channel") or
        entry.get("name") or
        ""
    ).strip()

def extract_link(links, platform):
    if not isinstance(links, list):
        return ""
    for link in links:
        if isinstance(link, dict):
            name = link.get("name", "").lower()
            url = link.get("url", "")
            if platform == "Instagram" and "instagram" in name:
                return url
            if platform == "Twitter" and "twitter" in name:
                return url
            if platform == "eBay" and "ebay" in name:
                return url
            if platform == "Mercari" and "mercari" in name:
                return url
            if platform == "Poshmark" and "poshmark" in name:
                return url
    return ""

def extract_other_links(links):
    platforms = ["instagram", "twitter", "ebay", "mercari", "poshmark"]
    other_links = []
    if not isinstance(links, list):
        return ""
    for link in links:
        if isinstance(link, dict):
            name = link.get("name", "").lower()
            url = link.get("url", "")
            if not any(p in name for p in platforms) and url:
                other_links.append(url)
        elif isinstance(link, str):
            if link:
                other_links.append(link)
    return "; ".join(other_links)

def load_campaign_urls(path):
    urls = set()
    with open(path, encoding="latin-1") as f:
        first_line = f.readline()
        f.seek(0)
        delimiter = ";" if ";" in first_line else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            url = row.get("youtube") or row.get("Channel URLs") or row.get("channel_url")
            if url and "youtube.com" in url:
                urls.add(normalize_youtube_url(url))
    return urls

def main():
    with open(input_json, encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    channels = v
                    break
            else:
                raise ValueError("Nu am găsit o listă de canale în input!")
        elif isinstance(data, list):
            channels = data
        else:
            raise ValueError("Format necunoscut pentru input!")

    # 1. Set cu toate URL-urile din campaign_tracking.csv
    campaign_urls = load_campaign_urls(campaign_csv)

    # 2. Construim un dict cu toate aparițiile URL-urilor din baza noastră
    url_to_entries = {}
    for entry in channels:
        url = extract_url(entry)
        if not url:
            continue
        url_to_entries.setdefault(url, []).append(entry)

    filtered = []
    duplicates = []
    for url, entries in url_to_entries.items():
        if url in campaign_urls:
            # Dacă există și în campaign_tracking, eliminăm complet toate aparițiile
            duplicates.extend(entries)
        else:
            # Dacă nu există în campaign_tracking, păstrăm doar una (prima)
            filtered.append(entries[0])

    print(f"Canale eliminate (existente în campaign_tracking sau duplicate locale): {len(duplicates)}")
    print(f"Canale rămase (unice și noi): {len(filtered)}")

    # Salvează duplicatele într-un CSV
    with open("duplicate_channels.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Channel", "URL"])
        for entry in duplicates:
            channel_name = extract_channel_name(entry)
            url = extract_url(entry)
            writer.writerow([channel_name, url])

    # Salvează unicele într-un CSV
    with open("unique_channels.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Channel", "URL"])
        for entry in filtered:
            channel_name = extract_channel_name(entry)
            url = extract_url(entry)
            writer.writerow([channel_name, url])

    print("Am salvat duplicatele în duplicate_channels.csv și unicele în unique_channels.csv")

    # Salvează rezultatul filtrat în JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    print(f"Rezultatul a fost salvat în {output_json}")

    # Pregătește datele pentru Excel
    rows = []
    today = datetime.now().strftime("%Y-%m-%d")
    for entry in filtered:
        channel_name = extract_channel_name(entry)
        url = extract_url(entry)
        subscribers = entry.get("subscribers") or entry.get("subscriberCount") or entry.get("Subscribers") or ""
        email = entry.get("email") or entry.get("Email") or ""
        links = entry.get("links") or []
        row = {
            "Channel": channel_name,
            "URL": url,
            "Subscribers": subscribers,
            "Notes": "",
            "Email": email,
            "Data": today,
            "Instagram Link": extract_link(links, "Instagram"),
            "Twitter Link": extract_link(links, "Twitter"),
            "eBay Link": extract_link(links, "eBay"),
            "Mercari Link": extract_link(links, "Mercari"),
            "Poshmark Link": extract_link(links, "Poshmark"),
            "Website/Linktree/Other Links": extract_other_links(links)
        }
        rows.append(row)

    columns = [
        "Channel", "URL", "Subscribers", "Notes", "Email", "Data",
        "Instagram Link", "Twitter Link", "eBay Link", "Mercari Link", "Poshmark Link", "Website/Linktree/Other Links"
    ]
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(output_excel, index=False)
    print(f"Rezultatul a fost salvat în {output_excel}")

    # --- ADAUGARE AUTOMATA IN campaign_tracking.csv ---
    # Mapare explicită la CSV-ul tău!
    with open(campaign_csv, encoding="latin-1") as f:
        first_line = f.readline()
        f.seek(0)
        delimiter = ";" if ";" in first_line else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        csv_fields = reader.fieldnames

    to_append = []
    for entry in rows:
        csv_row = {col: "" for col in csv_fields}
        # Mapping explicit
        csv_row["influencer"] = entry.get("Channel", "")
        csv_row["youtube"] = entry.get("URL", "")
        # Scoatem orice "subs" din subscribers
        subscribers = entry.get("Subscribers", "")
        if isinstance(subscribers, str):
            # extrage doar numărul, fără text
            subscribers = re.sub(r"\s?(youtube)?\s?subscribers?", "", subscribers, flags=re.IGNORECASE).strip()
        csv_row["# of Youtube followers"] = subscribers
        csv_row["NOTES"] = entry.get("Notes", "")
        csv_row["email"] = entry.get("Email", "")
        csv_row["contact date"] = entry.get("Data", "")
        # Restul câmpurilor rămân goale sau default
        to_append.append(csv_row)

    # Adaugă rândurile noi în campaign_tracking.csv
    with open(campaign_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, delimiter=delimiter)
        for row in to_append:
            writer.writerow(row)

    print(f"Am adăugat {len(to_append)} canale noi în {campaign_csv}")

if __name__ == "__main__":
    main()
