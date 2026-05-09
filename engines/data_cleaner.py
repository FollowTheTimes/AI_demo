import re

from config import OUTPUT_DIR


class DataCleaner:

    ID_CARD_WEIGHTS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    ID_CARD_CHECK_CODES = "10X98765432"

    JDBZ_MAP = {
        "贷": "进",
        "贷方": "进",
        "收入": "进",
        "入": "进",
        "借": "出",
        "借方": "出",
        "支出": "出",
    }

    ALL_RULES = ["id_card", "phone", "amount", "deduplicate", "datetime", "jdbz", "empty"]

    def clean(self, data, rules=None):
        if not data:
            return []

        if rules is None or len(rules) == 0:
            rules = self.ALL_RULES

        cleaned = []
        anomaly_count = 0

        for row in data:
            record = dict(row)
            has_anomaly = False

            if "id_card" in rules and "sfzh" in record and record["sfzh"]:
                is_valid, normalized = self.validate_id_card(record["sfzh"])
                record["sfzh"] = normalized
                if not is_valid:
                    record["_id_card_anomaly"] = True
                    has_anomaly = True

            if "phone" in rules and "zysm" in record and record["zysm"]:
                phones = self.extract_phones(record["zysm"])
                if phones:
                    record["_extracted_phones"] = phones

            if "amount" in rules and "jy_je" in record:
                record["jy_je"] = self.normalize_amount(record["jy_je"])

            if "datetime" in rules and "sj" in record and record["sj"]:
                record["sj"] = self.normalize_datetime(record["sj"])

            if "jdbz" in rules and "jdbz" in record and record["jdbz"]:
                jdbz = str(record["jdbz"]).strip()
                if jdbz not in ("进", "出"):
                    record["jdbz"] = self.JDBZ_MAP.get(jdbz, jdbz)

            if "empty" in rules:
                for key in list(record.keys()):
                    if isinstance(record[key], str) and record[key].strip() == "":
                        record[key] = None

            if has_anomaly:
                anomaly_count += 1

            cleaned.append(record)

        if "deduplicate" in rules:
            cleaned = self.remove_duplicates(cleaned)

        return cleaned

    def validate_id_card(self, id_card):
        if not id_card:
            return False, None

        id_card = str(id_card).strip().upper()

        if len(id_card) != 18:
            return False, id_card

        if not re.match(r"^\d{17}[\dX]$", id_card):
            return False, id_card

        try:
            total = 0
            for i in range(17):
                total += int(id_card[i]) * self.ID_CARD_WEIGHTS[i]

            check_code = self.ID_CARD_CHECK_CODES[total % 11]

            if id_card[17] == check_code:
                return True, id_card
            else:
                return False, id_card
        except (ValueError, IndexError):
            return False, id_card

    def extract_phones(self, text):
        if not text:
            return []

        text = str(text)
        pattern = r"(?<!\d)1[3-9]\d{9}(?!\d)"
        phones = re.findall(pattern, text)
        return phones

    def normalize_amount(self, value):
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        value = str(value).strip()
        value = re.sub(r"[^\d.\-]", "", value)

        if not value or value == "-" or value == ".":
            return 0.0

        try:
            return float(value)
        except ValueError:
            return 0.0

    def remove_duplicates(self, data):
        if not data:
            return []

        seen = set()
        result = []

        for row in data:
            key = None

            if "jylsh" in row and row["jylsh"]:
                key = ("jylsh", str(row["jylsh"]))
            else:
                parts = []
                for field in ("jy_zh", "sj", "jy_je"):
                    if field in row and row[field] is not None:
                        parts.append(str(row[field]))
                if len(parts) == 3:
                    key = ("combo", "|".join(parts))

            if key is None or key not in seen:
                if key is not None:
                    seen.add(key)
                result.append(row)

        return result

    def normalize_datetime(self, value):
        if not value:
            return None

        value = str(value).strip()

        patterns = [
            r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})$",
            r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2})$",
            r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$",
            r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$",
            r"^(\d{4})(\d{2})(\d{2})$",
        ]

        for pattern in patterns:
            match = re.match(pattern, value)
            if match:
                groups = match.groups()
                year = groups[0]
                month = groups[1].zfill(2)
                day = groups[2].zfill(2)

                if len(groups) >= 6:
                    hour = groups[3].zfill(2)
                    minute = groups[4].zfill(2)
                    second = groups[5].zfill(2)
                elif len(groups) >= 5:
                    hour = groups[3].zfill(2)
                    minute = groups[4].zfill(2)
                    second = "00"
                else:
                    hour = "00"
                    minute = "00"
                    second = "00"

                return f"{year}-{month}-{day} {hour}:{minute}:{second}"

        return value

    def generate_clean_report(self, original_data, cleaned_data):
        original_count = len(original_data) if original_data else 0
        cleaned_count = len(cleaned_data) if cleaned_data else 0
        removed_count = original_count - cleaned_count

        anomaly_count = sum(
            1 for row in cleaned_data if row.get("_id_card_anomaly")
        )
        phone_extracted_count = sum(
            1 for row in cleaned_data if row.get("_extracted_phones")
        )

        report = {
            "原始数据条数": original_count,
            "清洗后数据条数": cleaned_count,
            "去除重复条数": removed_count,
            "身份证异常条数": anomaly_count,
            "提取到手机号条数": phone_extracted_count,
        }

        return report
