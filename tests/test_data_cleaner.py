import pytest
from engines.data_cleaner import DataCleaner


@pytest.fixture
def cleaner():
    return DataCleaner()


class TestIdCardValidation:
    def test_valid_id_card(self, cleaner):
        is_valid, normalized = cleaner.validate_id_card("110101199001011234")
        assert isinstance(is_valid, bool)
        assert normalized is not None

    def test_empty_id_card(self, cleaner):
        is_valid, normalized = cleaner.validate_id_card("")
        assert is_valid is False

    def test_none_id_card(self, cleaner):
        is_valid, normalized = cleaner.validate_id_card(None)
        assert is_valid is False

    def test_short_id_card(self, cleaner):
        is_valid, normalized = cleaner.validate_id_card("123456")
        assert is_valid is False


class TestPhoneExtraction:
    def test_extract_from_text(self, cleaner):
        phones = cleaner.extract_phones("联系电话13800138000和13912345678")
        assert len(phones) == 2
        assert "13800138000" in phones

    def test_no_phone(self, cleaner):
        phones = cleaner.extract_phones("没有手机号")
        assert len(phones) == 0

    def test_empty_text(self, cleaner):
        phones = cleaner.extract_phones("")
        assert len(phones) == 0


class TestAmountNormalization:
    def test_string_amount(self, cleaner):
        assert cleaner.normalize_amount("1,000.50") == 1000.50

    def test_numeric_amount(self, cleaner):
        assert cleaner.normalize_amount(100) == 100.0

    def test_none_amount(self, cleaner):
        assert cleaner.normalize_amount(None) == 0.0

    def test_empty_string(self, cleaner):
        assert cleaner.normalize_amount("") == 0.0


class TestDatetimeNormalization:
    def test_standard_format(self, cleaner):
        result = cleaner.normalize_datetime("2024-01-15 10:30:00")
        assert result == "2024-01-15 10:30:00"

    def test_slash_format(self, cleaner):
        result = cleaner.normalize_datetime("2024/01/15 10:30:00")
        assert result == "2024-01-15 10:30:00"

    def test_compact_format(self, cleaner):
        result = cleaner.normalize_datetime("20240115103000")
        assert result == "2024-01-15 10:30:00"

    def test_date_only(self, cleaner):
        result = cleaner.normalize_datetime("2024-01-15")
        assert result == "2024-01-15 00:00:00"

    def test_empty(self, cleaner):
        assert cleaner.normalize_datetime("") is None


class TestDeduplication:
    def test_remove_duplicates_by_jylsh(self, cleaner):
        data = [
            {"jylsh": "001", "jy_je": 100},
            {"jylsh": "001", "jy_je": 100},
            {"jylsh": "002", "jy_je": 200},
        ]
        result = cleaner.remove_duplicates(data)
        assert len(result) == 2

    def test_remove_duplicates_by_combo(self, cleaner):
        data = [
            {"jy_zh": "A001", "sj": "2024-01-01", "jy_je": 100},
            {"jy_zh": "A001", "sj": "2024-01-01", "jy_je": 100},
            {"jy_zh": "A002", "sj": "2024-01-01", "jy_je": 200},
        ]
        result = cleaner.remove_duplicates(data)
        assert len(result) == 2

    def test_no_duplicates(self, cleaner):
        data = [
            {"jylsh": "001", "jy_je": 100},
            {"jylsh": "002", "jy_je": 200},
        ]
        result = cleaner.remove_duplicates(data)
        assert len(result) == 2


class TestCleanWithRules:
    def test_clean_with_all_rules(self, cleaner):
        data = [
            {"sfzh": "110101199001011234", "jy_je": "1,000", "jdbz": "贷", "sj": "2024/01/15 10:30:00"},
        ]
        result = cleaner.clean(data)
        assert len(result) == 1
        assert result[0]["jy_je"] == 1000.0
        assert result[0]["jdbz"] == "进"

    def test_clean_with_specific_rules(self, cleaner):
        data = [
            {"jy_je": "1,000", "jdbz": "贷"},
        ]
        result = cleaner.clean(data, rules=["amount"])
        assert len(result) == 1
        assert result[0]["jy_je"] == 1000.0

    def test_clean_empty_data(self, cleaner):
        result = cleaner.clean([])
        assert result == []

    def test_clean_none_data(self, cleaner):
        result = cleaner.clean(None)
        assert result == []

    def test_rules_filter_id_card_only(self, cleaner):
        data = [
            {"sfzh": "12345", "jy_je": "abc"},
        ]
        result = cleaner.clean(data, rules=["id_card"])
        assert result[0].get("_id_card_anomaly") is True
        assert result[0]["jy_je"] == "abc"

    def test_rules_filter_amount_only(self, cleaner):
        data = [
            {"sfzh": "12345", "jy_je": "1,000"},
        ]
        result = cleaner.clean(data, rules=["amount"])
        assert result[0]["jy_je"] == 1000.0
        assert "_id_card_anomaly" not in result[0]


class TestJdbzNormalization:
    def test_normalize_dai_to_jin(self, cleaner):
        data = [{"jdbz": "贷"}]
        result = cleaner.clean(data)
        assert result[0]["jdbz"] == "进"

    def test_normalize_jie_to_chu(self, cleaner):
        data = [{"jdbz": "借"}]
        result = cleaner.clean(data)
        assert result[0]["jdbz"] == "出"

    def test_already_normalized(self, cleaner):
        data = [{"jdbz": "进"}]
        result = cleaner.clean(data)
        assert result[0]["jdbz"] == "进"


class TestEmptyValueHandling:
    def test_empty_string_becomes_null(self, cleaner):
        data = [{"name": "  ", "value": "test"}]
        result = cleaner.clean(data)
        assert result[0]["name"] is None
        assert result[0]["value"] == "test"


class TestCleanReport:
    def test_report_structure(self, cleaner):
        original = [{"jylsh": "001"}, {"jylsh": "001"}, {"jylsh": "002"}]
        cleaned = cleaner.clean(original)
        report = cleaner.generate_clean_report(original, cleaned)
        assert "原始数据条数" in report
        assert "清洗后数据条数" in report
        assert "去除重复条数" in report

    def test_report_counts(self, cleaner):
        original = [{"jylsh": "001"}, {"jylsh": "001"}, {"jylsh": "002"}]
        cleaned = cleaner.clean(original)
        report = cleaner.generate_clean_report(original, cleaned)
        assert report["原始数据条数"] == 3
        assert report["清洗后数据条数"] == 2
        assert report["去除重复条数"] == 1
