CREATE DATABASE  IF NOT EXISTS `energia_etoil` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `energia_etoil`;
-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: energia_etoil
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dim_equipement`
--

DROP TABLE IF EXISTS `dim_equipement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_equipement` (
  `id_equipement` int NOT NULL,
  `equipement_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_site` int DEFAULT NULL,
  `id_modele` int DEFAULT NULL,
  `modele_code` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `type_equipement` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `puissance_nominale_w` decimal(10,2) DEFAULT NULL,
  `est_producteur` tinyint(1) DEFAULT NULL,
  `statut` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `date_installation` date DEFAULT NULL,
  PRIMARY KEY (`id_equipement`),
  KEY `fk_equipement_site` (`id_site`),
  KEY `fk_equipement_modele` (`id_modele`),
  CONSTRAINT `fk_equipement_modele` FOREIGN KEY (`id_modele`) REFERENCES `dim_modele` (`id_modele`),
  CONSTRAINT `fk_equipement_site` FOREIGN KEY (`id_site`) REFERENCES `dim_site` (`id_site`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_equipement`
--

LOCK TABLES `dim_equipement` WRITE;
/*!40000 ALTER TABLE `dim_equipement` DISABLE KEYS */;
/*!40000 ALTER TABLE `dim_equipement` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_modele`
--

DROP TABLE IF EXISTS `dim_modele`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_modele` (
  `id_modele` int NOT NULL,
  `modele_id` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `type_equipement` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fabricant` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `puissance_nominale_w` decimal(10,2) DEFAULT NULL,
  `rendement_nominal` decimal(4,3) DEFAULT NULL,
  `duree_vie_annees` smallint DEFAULT NULL,
  `masse_kg` decimal(6,2) DEFAULT NULL,
  PRIMARY KEY (`id_modele`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_modele`
--

LOCK TABLES `dim_modele` WRITE;
/*!40000 ALTER TABLE `dim_modele` DISABLE KEYS */;
/*!40000 ALTER TABLE `dim_modele` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_phase`
--

DROP TABLE IF EXISTS `dim_phase`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_phase` (
  `id_phase` int NOT NULL,
  `phase` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `production_attendue` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id_phase`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_phase`
--

LOCK TABLES `dim_phase` WRITE;
/*!40000 ALTER TABLE `dim_phase` DISABLE KEYS */;
/*!40000 ALTER TABLE `dim_phase` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_site`
--

DROP TABLE IF EXISTS `dim_site`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_site` (
  `id_site` int NOT NULL,
  `site_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nom` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orbite_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `altitude_km` decimal(6,2) DEFAULT NULL,
  `inclination_deg` decimal(5,2) DEFAULT NULL,
  `capacite_max_kw` decimal(8,2) DEFAULT NULL,
  `zone_orbitale` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `statut` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_site`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_site`
--

LOCK TABLES `dim_site` WRITE;
/*!40000 ALTER TABLE `dim_site` DISABLE KEYS */;
/*!40000 ALTER TABLE `dim_site` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_temps`
--

DROP TABLE IF EXISTS `dim_temps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_temps` (
  `id_temps` int NOT NULL,
  `timestamp` datetime NOT NULL,
  `date` date DEFAULT NULL,
  `annee` smallint DEFAULT NULL,
  `mois` tinyint DEFAULT NULL,
  `jour` tinyint DEFAULT NULL,
  `heure` tinyint DEFAULT NULL,
  `minute` tinyint DEFAULT NULL,
  `jour_semaine` tinyint DEFAULT NULL,
  `semaine` tinyint DEFAULT NULL,
  `creneau_orbital` datetime DEFAULT NULL,
  PRIMARY KEY (`id_temps`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_temps`
--

LOCK TABLES `dim_temps` WRITE;
/*!40000 ALTER TABLE `dim_temps` DISABLE KEYS */;
/*!40000 ALTER TABLE `dim_temps` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_type_alarme`
--

DROP TABLE IF EXISTS `dim_type_alarme`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_type_alarme` (
  `id_type_alarme` int NOT NULL,
  `type_alarme` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seuil_warning` decimal(8,2) DEFAULT NULL,
  `seuil_critical` decimal(8,2) DEFAULT NULL,
  `unite` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_type_alarme`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_type_alarme`
--

LOCK TABLES `dim_type_alarme` WRITE;
/*!40000 ALTER TABLE `dim_type_alarme` DISABLE KEYS */;
/*!40000 ALTER TABLE `dim_type_alarme` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fait_alarme`
--

DROP TABLE IF EXISTS `fait_alarme`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fait_alarme` (
  `alarme_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_temps` int DEFAULT NULL,
  `id_equipement` int DEFAULT NULL,
  `id_type_alarme` int DEFAULT NULL,
  `severite` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `est_critique` tinyint(1) DEFAULT NULL,
  `acquittee` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`alarme_id`),
  KEY `fk_alarme_temps` (`id_temps`),
  KEY `fk_alarme_equipement` (`id_equipement`),
  KEY `fk_alarme_type` (`id_type_alarme`),
  CONSTRAINT `fk_alarme_equipement` FOREIGN KEY (`id_equipement`) REFERENCES `dim_equipement` (`id_equipement`),
  CONSTRAINT `fk_alarme_temps` FOREIGN KEY (`id_temps`) REFERENCES `dim_temps` (`id_temps`),
  CONSTRAINT `fk_alarme_type` FOREIGN KEY (`id_type_alarme`) REFERENCES `dim_type_alarme` (`id_type_alarme`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fait_alarme`
--

LOCK TABLES `fait_alarme` WRITE;
/*!40000 ALTER TABLE `fait_alarme` DISABLE KEYS */;
/*!40000 ALTER TABLE `fait_alarme` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fait_maintenance`
--

DROP TABLE IF EXISTS `fait_maintenance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fait_maintenance` (
  `maintenance_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_equipement` int DEFAULT NULL,
  `id_temps_debut` int DEFAULT NULL,
  `id_temps_fin` int DEFAULT NULL,
  `type_intervention` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `technicien` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cout_eur` decimal(10,2) DEFAULT NULL,
  `duree_jours` decimal(8,2) DEFAULT NULL,
  PRIMARY KEY (`maintenance_id`),
  KEY `fk_maint_equipement` (`id_equipement`),
  KEY `fk_maint_debut` (`id_temps_debut`),
  KEY `fk_maint_fin` (`id_temps_fin`),
  CONSTRAINT `fk_maint_debut` FOREIGN KEY (`id_temps_debut`) REFERENCES `dim_temps` (`id_temps`),
  CONSTRAINT `fk_maint_equipement` FOREIGN KEY (`id_equipement`) REFERENCES `dim_equipement` (`id_equipement`),
  CONSTRAINT `fk_maint_fin` FOREIGN KEY (`id_temps_fin`) REFERENCES `dim_temps` (`id_temps`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fait_maintenance`
--

LOCK TABLES `fait_maintenance` WRITE;
/*!40000 ALTER TABLE `fait_maintenance` DISABLE KEYS */;
/*!40000 ALTER TABLE `fait_maintenance` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fait_mesure`
--

DROP TABLE IF EXISTS `fait_mesure`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fait_mesure` (
  `id_temps` int NOT NULL,
  `id_equipement` int NOT NULL,
  `id_site` int DEFAULT NULL,
  `id_phase` int DEFAULT NULL,
  `puissance_w` decimal(10,2) DEFAULT NULL,
  `temperature_c` decimal(5,2) DEFAULT NULL,
  `tension_v` decimal(5,2) DEFAULT NULL,
  `courant_a` decimal(5,2) DEFAULT NULL,
  `rayonnement` decimal(5,3) DEFAULT NULL,
  `puissance_attendue_w` decimal(10,2) DEFAULT NULL,
  `performance` decimal(8,4) DEFAULT NULL,
  `ecart_w` decimal(10,2) DEFAULT NULL,
  `energie_wh` decimal(10,4) DEFAULT NULL,
  `energie_attendue_wh` decimal(10,4) DEFAULT NULL,
  `perte_wh` decimal(10,4) DEFAULT NULL,
  PRIMARY KEY (`id_temps`,`id_equipement`),
  KEY `fk_mesure_equipement` (`id_equipement`),
  KEY `fk_mesure_site` (`id_site`),
  KEY `fk_mesure_phase` (`id_phase`),
  CONSTRAINT `fk_mesure_equipement` FOREIGN KEY (`id_equipement`) REFERENCES `dim_equipement` (`id_equipement`),
  CONSTRAINT `fk_mesure_phase` FOREIGN KEY (`id_phase`) REFERENCES `dim_phase` (`id_phase`),
  CONSTRAINT `fk_mesure_site` FOREIGN KEY (`id_site`) REFERENCES `dim_site` (`id_site`),
  CONSTRAINT `fk_mesure_temps` FOREIGN KEY (`id_temps`) REFERENCES `dim_temps` (`id_temps`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fait_mesure`
--

LOCK TABLES `fait_mesure` WRITE;
/*!40000 ALTER TABLE `fait_mesure` DISABLE KEYS */;
/*!40000 ALTER TABLE `fait_mesure` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'energia_etoil'
--

--
-- Dumping routines for database 'energia_etoil'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-23 10:55:01
