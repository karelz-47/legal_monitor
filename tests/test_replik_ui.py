import unittest

import replik_ui


class ReplikUiTests(unittest.TestCase):
    def test_known_codes_are_localized_and_raw_preserved(self):
        record = {
            "dataset": "konanie",
            "Id": "8647",
            "Typ": "KONKURZ",
            "StavKonania": "SKONCENY_PROCES",
            "Dlznik": "eMTrade a.s.",
            "Ico": "36628760",
            "SudNazov": "Okresný súd Banská Bystrica",
            "SpisovaZnackaSudu": "2K/98/2016",
        }

        payload = replik_ui.build_ui_payload([record], search_mode="ico", query={"ico": "36628760"})
        card = payload["cards"][0]

        self.assertEqual(card["title"], "Konkurz")
        self.assertEqual(card["severity"], "critical")
        self.assertEqual(card["badges"][0]["rawCode"], "KONKURZ")
        self.assertEqual(payload["summary"]["proceedingsCount"], 1)

    def test_unknown_codes_are_humanized(self):
        label = replik_ui.get_code_label("druhPodania", "NEW_UNKNOWN_CODE")

        self.assertEqual(label["label"], "New Unknown Code")
        self.assertEqual(label["code"], "NEW_UNKNOWN_CODE")
        self.assertEqual(label["severity"], "info")

    def test_notice_card_uses_filing_type_label(self):
        record = {
            "dataset": "oznam",
            "OznamId": "123",
            "OznamTyp": "OZNAM_SUD",
            "KonanieTyp": "KONKURZ",
            "DruhPodania": "INE_ZVEREJNENIE",
            "SudNazov": "Okresný súd Banská Bystrica",
            "SpisovaZnackaSudnehoSpisu": "2K/98/2016",
        }

        payload = replik_ui.build_ui_payload([record], search_mode="period", query={})
        card = payload["cards"][0]
        badge_labels = [badge["label"] for badge in card["badges"]]

        self.assertEqual(card["title"], "Oznam súdu · Konkurz")
        self.assertIn("Iné zverejnenie", badge_labels)
        self.assertNotIn("INE_ZVEREJNENIE", [card["title"], *badge_labels])


if __name__ == "__main__":
    unittest.main()
