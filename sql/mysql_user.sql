-- Run once as administrator. The generated password is displayed by MySQL.
CREATE USER 'currency_judge'@'localhost' IDENTIFIED BY RANDOM PASSWORD;
GRANT SELECT, INSERT ON currency_judge.* TO 'currency_judge'@'localhost';
