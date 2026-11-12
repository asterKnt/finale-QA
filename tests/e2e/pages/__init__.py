"""Definicion de Page Object Model (POM) con principios SOLID para pruebas E2E."""

from tests.e2e.pages.analytics_page import AnalyticsPage
from tests.e2e.pages.base_page import BasePage, IPage
from tests.e2e.pages.campaign_page import CampaignPage
from tests.e2e.pages.dashboard_page import DashboardPage

__all__ = [
    "AnalyticsPage",
    "BasePage",
    "CampaignPage",
    "DashboardPage",
    "IPage",
]
