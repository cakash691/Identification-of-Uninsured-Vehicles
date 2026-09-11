-- setup_mysql.sql -- run once (as root/admin) before generate_data.py.
-- Creates the application user and the 5 databases: 4 sources + warehouse.
-- Usage: mysql -u root -p < setup_mysql.sql

CREATE USER IF NOT EXISTS 'iia_app'@'127.0.0.1' IDENTIFIED BY 'iia_app_pw';

CREATE DATABASE IF NOT EXISTS roadcapture;
CREATE DATABASE IF NOT EXISTS insurance;
CREATE DATABASE IF NOT EXISTS rto_registration;
CREATE DATABASE IF NOT EXISTS theft_records;
CREATE DATABASE IF NOT EXISTS vehicle_dwh;

GRANT ALL PRIVILEGES ON roadcapture.*       TO 'iia_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON insurance.*         TO 'iia_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON rto_registration.*  TO 'iia_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON theft_records.*     TO 'iia_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON vehicle_dwh.*       TO 'iia_app'@'127.0.0.1';

FLUSH PRIVILEGES;
