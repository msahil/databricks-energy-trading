-- Unity Catalog bootstrap for forecasting demo data (see ../README.md → unity_catalog.schemas).
-- Run once in a SQL warehouse if the schema does not exist or your user lacks CREATE SCHEMA on this catalog.
-- Identifiers use underscores; backticks keep them explicit in SQL.

CREATE SCHEMA IF NOT EXISTS `energy_utilities`.`energy_trading2`
COMMENT 'Energy trading forecasting demos (Databricks Delta tables seeded by modules/forecasting/notebooks/*.ipynb)';
