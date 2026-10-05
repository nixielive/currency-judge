CREATE DATABASE IF NOT EXISTS currency_judge CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
USE currency_judge;
CREATE TABLE IF NOT EXISTS collection_runs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    started_at VARCHAR(32) NOT NULL,
    completed_at VARCHAR(32) NOT NULL,
    status VARCHAR(5) NOT NULL CHECK (status IN ('OK', 'ERROR')),
    error TEXT,
    payload_json LONGTEXT
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS quotes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT UNSIGNED NOT NULL,
    provider VARCHAR(32) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    bid TEXT NOT NULL,
    ask TEXT NOT NULL,
    mid TEXT NOT NULL,
    price_time VARCHAR(32) NOT NULL,
    received_at VARCHAR(32) NOT NULL,
    market_status VARCHAR(8) NOT NULL,
    quality VARCHAR(8) NOT NULL,
    FOREIGN KEY (run_id) REFERENCES collection_runs(id),
    UNIQUE KEY quotes_run_symbol (run_id, symbol),
    KEY quotes_symbol_time (symbol, received_at)
) ENGINE=InnoDB;
