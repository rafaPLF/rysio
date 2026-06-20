from __future__ import annotations


class PremiumService:
    def get_panel_limit(self, plan: str, *, unlimited: bool = False) -> int:
        if unlimited:
            return 999_999
        return 1 if plan == "free" else 5

    def has_feature(self, plan: str, feature_key: str) -> bool:
        free_features = {
            "autoroles.basic",
            "tickets.basic",
            "verification.basic",
            "antispam.basic",
            "lfg.basic",
        }
        premium_features = {
            "tickets.multi_panel",
            "verification.advanced",
            "antispam.advanced",
            "lfg.priority",
        }

        if feature_key in free_features:
            return True

        return plan != "free" and feature_key in premium_features
