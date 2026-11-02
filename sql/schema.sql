-- Daily city-wide averages for Mexico City (SIMAT: RAMA pollutants + REDMET meteorology)
-- Gases in ppb (CO in ppm), particles in µg/m³.

DROP TABLE IF EXISTS pollutants;
CREATE TABLE pollutants (
    fecha  DATE PRIMARY KEY,
    co     REAL,  -- ppm
    no     REAL,  -- ppb
    no2    REAL,  -- ppb
    nox    REAL,  -- ppb
    o3     REAL,  -- ppb
    pm10   REAL,  -- µg/m³
    pm25   REAL,  -- µg/m³
    so2    REAL   -- ppb
);

DROP TABLE IF EXISTS meteo;
CREATE TABLE meteo (
    fecha  DATE PRIMARY KEY,
    rh     REAL,  -- relative humidity, %
    tmp    REAL,  -- temperature, °C
    wdr    REAL,  -- wind direction, degrees
    wsp    REAL   -- wind speed, m/s
);

DROP VIEW IF EXISTS daily;
CREATE VIEW daily AS
SELECT p.*, m.rh, m.tmp, m.wdr, m.wsp,
       CAST(strftime('%Y', p.fecha) AS INTEGER) AS year,
       CAST(strftime('%m', p.fecha) AS INTEGER) AS month,
       CAST(strftime('%w', p.fecha) AS INTEGER) AS weekday   -- 0 = Sunday
FROM pollutants p
JOIN meteo m USING (fecha);
