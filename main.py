from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import requests


def load_credentials(username):
    """はてなAPIアクセスに必要な認証情報をタプルの形式で返す"""
    auth_token = os.getenv("HATENA_BLOG_ATOMPUB_KEY")
    message = "環境変数`HATENA_BLOG_ATOMPUB_KEY`にAtomPubのAPIキーを設定してください"
    assert auth_token, message
    return (username, auth_token)


def retrieve_hatena_blog_entries(blog_entries_url, user_pass_tuple):
    """はてなブログAPIにGETアクセスし、記事一覧を表すXMLを文字列で返す"""
    r = requests.get(blog_entries_url, auth=user_pass_tuple)
    return r.text


def select_elements_of_tag(xml_root, tag):
    """返り値のXMLを解析し、指定したタグを持つ子要素をすべて返す"""
    return xml_root.findall(tag)


def return_next_entry_list_url(links):
    """続くブログ記事一覧のエンドポイントを返す"""
    for link in links:
        if link.attrib["rel"] == "next":
            return link.attrib["href"]


def is_draft(entry):
    """ブログ記事がドラフトかどうか判定する"""
    draft_status = (
        entry.find("{http://www.w3.org/2007/app}control")
        .find("{http://www.w3.org/2007/app}draft")
        .text
    )
    return draft_status == "yes"


def return_published_date(entry):
    """ブログ記事の公開日を返す

    ドラフトの場合も返される仕様だった
    """
    publish_date_str = entry.find(
        "{http://www.w3.org/2005/Atom}published"
    ).text
    return datetime.fromisoformat(publish_date_str)


def is_in_period(datetime_, start, end):
    """指定した日時がstartからendまでの期間に含まれるか判定する"""
    return start <= datetime_ < end


def return_id(entry):
    """ブログのURIに含まれるID部分を返す"""
    link = entry.find("{http://www.w3.org/2005/Atom}link")
    uri = link.attrib["href"]
    return uri.split("/")[-1]


def return_contents(entry):
    """ブログのタイトルと本文をつなげて返す"""
    title = entry.find("{http://www.w3.org/2005/Atom}title").text
    content = entry.find("{http://www.w3.org/2005/Atom}content").text
    return f"{title}。\n\n{content}"


if __name__ == "__main__":
    user_pass_tuple = load_credentials("nikkie-ftnext")

    blog_entries_url = "https://blog.hatena.ne.jp/nikkie-ftnext/nikkie-ftnext.hatenablog.com/atom/entry"

    jst_tz = timezone(timedelta(seconds=32400))
    date_range_start = datetime(2019, 1, 1, tzinfo=jst_tz)
    date_range_end = datetime(2020, 1, 1, tzinfo=jst_tz)

    oldest_published_date = datetime.now(jst_tz)
    target_entries = []

    while date_range_start <= oldest_published_date:
        entries_xml = retrieve_hatena_blog_entries(
            blog_entries_url, user_pass_tuple
        )
        root = ET.fromstring(entries_xml)

        links = select_elements_of_tag(
            root, "{http://www.w3.org/2005/Atom}link"
        )
        blog_entries_url = return_next_entry_list_url(links)

        entries = select_elements_of_tag(
            root, "{http://www.w3.org/2005/Atom}entry"
        )
        for entry in entries:
            if is_draft(entry):
                continue
            oldest_published_date = return_published_date(entry)
            if is_in_period(
                oldest_published_date, date_range_start, date_range_end
            ):
                target_entries.append(entry)
        print(f"{oldest_published_date}までの記事を取得（全{len(target_entries)}件）")

    output_path = Path("entries_2019")
    output_path.mkdir(exist_ok=True)

    for entry in target_entries:
        id_ = return_id(entry)
        file_path = output_path / f"{id_}.txt"
        contents = return_contents(entry)
        with open(file_path, "w") as fout:
            fout.write(contents)
