-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: energia_flux
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
-- Table structure for table `alarme`
--

DROP TABLE IF EXISTS `alarme`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alarme` (
  `alarme_id` varchar(20) NOT NULL,
  `equipement_id` varchar(20) NOT NULL,
  `type_alarme` varchar(30) NOT NULL,
  `horodatage` datetime DEFAULT NULL,
  `severite` varchar(20) DEFAULT NULL,
  `message` varchar(200) DEFAULT NULL,
  `acquittee` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`alarme_id`),
  KEY `fk_alarme_equipement` (`equipement_id`),
  KEY `fk_alarme_type` (`type_alarme`),
  CONSTRAINT `fk_alarme_equipement` FOREIGN KEY (`equipement_id`) REFERENCES `equipement` (`equipement_id`),
  CONSTRAINT `fk_alarme_type` FOREIGN KEY (`type_alarme`) REFERENCES `type_alarme` (`type_alarme`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alarme`
--

LOCK TABLES `alarme` WRITE;
/*!40000 ALTER TABLE `alarme` DISABLE KEYS */;
/*!40000 ALTER TABLE `alarme` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `equipement`
--

DROP TABLE IF EXISTS `equipement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `equipement` (
  `equipement_id` varchar(20) NOT NULL,
  `site_id` varchar(20) NOT NULL,
  `type_equipement` varchar(30) DEFAULT NULL,
  `modele_id` varchar(30) DEFAULT NULL,
  `puissance_nominale_w` decimal(10,2) DEFAULT NULL,
  `date_installation` date DEFAULT NULL,
  `statut` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`equipement_id`),
  KEY `fk_equipement_site` (`site_id`),
  KEY `fk_equipement_modele` (`modele_id`),
  CONSTRAINT `fk_equipement_modele` FOREIGN KEY (`modele_id`) REFERENCES `modele` (`modele_id`),
  CONSTRAINT `fk_equipement_site` FOREIGN KEY (`site_id`) REFERENCES `site` (`site_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `equipement`
--

LOCK TABLES `equipement` WRITE;
/*!40000 ALTER TABLE `equipement` DISABLE KEYS */;
/*!40000 ALTER TABLE `equipement` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `etat_orbital`
--

DROP TABLE IF EXISTS `etat_orbital`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `etat_orbital` (
  `horodatage` datetime NOT NULL,
  `site_id` varchar(20) NOT NULL,
  `phase` varchar(20) DEFAULT NULL,
  `rayonnement_solaire_w_m2` decimal(8,2) DEFAULT NULL,
  `temperature_ambiante_c` decimal(5,2) DEFAULT NULL,
  PRIMARY KEY (`horodatage`,`site_id`),
  KEY `fk_etat_site` (`site_id`),
  CONSTRAINT `fk_etat_site` FOREIGN KEY (`site_id`) REFERENCES `site` (`site_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `etat_orbital`
--

LOCK TABLES `etat_orbital` WRITE;
/*!40000 ALTER TABLE `etat_orbital` DISABLE KEYS */;
/*!40000 ALTER TABLE `etat_orbital` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `intervention`
--

DROP TABLE IF EXISTS `intervention`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `intervention` (
  `maintenance_id` varchar(20) NOT NULL,
  `equipement_id` varchar(20) NOT NULL,
  `date_debut` date DEFAULT NULL,
  `date_fin` date DEFAULT NULL,
  `type_intervention` varchar(30) DEFAULT NULL,
  `technicien` varchar(30) DEFAULT NULL,
  `cout_eur` decimal(10,2) DEFAULT NULL,
  `commentaire` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`maintenance_id`),
  KEY `fk_intervention_equipement` (`equipement_id`),
  CONSTRAINT `fk_intervention_equipement` FOREIGN KEY (`equipement_id`) REFERENCES `equipement` (`equipement_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `intervention`
--

LOCK TABLES `intervention` WRITE;
/*!40000 ALTER TABLE `intervention` DISABLE KEYS */;
/*!40000 ALTER TABLE `intervention` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mesure`
--

DROP TABLE IF EXISTS `mesure`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mesure` (
  `horodatage` datetime NOT NULL,
  `equipement_id` varchar(20) NOT NULL,
  `puissance_w` decimal(10,2) DEFAULT NULL,
  `temperature_c` decimal(5,2) DEFAULT NULL,
  `tension_v` decimal(5,2) DEFAULT NULL,
  `courant_a` decimal(5,2) DEFAULT NULL,
  `rayonnement` decimal(5,3) DEFAULT NULL,
  PRIMARY KEY (`horodatage`,`equipement_id`),
  KEY `fk_mesure_equipement` (`equipement_id`),
  CONSTRAINT `fk_mesure_equipement` FOREIGN KEY (`equipement_id`) REFERENCES `equipement` (`equipement_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mesure`
--

LOCK TABLES `mesure` WRITE;
/*!40000 ALTER TABLE `mesure` DISABLE KEYS */;
/*!40000 ALTER TABLE `mesure` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `modele`
--

DROP TABLE IF EXISTS `modele`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `modele` (
  `modele_id` varchar(30) NOT NULL,
  `type_equipement` varchar(30) DEFAULT NULL,
  `fabricant` varchar(30) DEFAULT NULL,
  `puissance_nominale_w` decimal(10,2) DEFAULT NULL,
  `rendement_nominal` decimal(4,3) DEFAULT NULL,
  `duree_vie_annees` smallint DEFAULT NULL,
  `masse_kg` decimal(6,2) DEFAULT NULL,
  PRIMARY KEY (`modele_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `modele`
--

LOCK TABLES `modele` WRITE;
/*!40000 ALTER TABLE `modele` DISABLE KEYS */;
/*!40000 ALTER TABLE `modele` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `site`
--

DROP TABLE IF EXISTS `site`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `site` (
  `site_id` varchar(20) NOT NULL,
  `nom` varchar(50) DEFAULT NULL,
  `orbite_type` varchar(20) DEFAULT NULL,
  `altitude_km` decimal(6,2) DEFAULT NULL,
  `inclination_deg` decimal(5,2) DEFAULT NULL,
  `date_mise_en_service` date DEFAULT NULL,
  `statut` varchar(20) DEFAULT NULL,
  `description` varchar(100) DEFAULT NULL,
  `capacite_max_kw` decimal(8,2) DEFAULT NULL,
  `zone_orbitale` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`site_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `site`
--

LOCK TABLES `site` WRITE;
/*!40000 ALTER TABLE `site` DISABLE KEYS */;
/*!40000 ALTER TABLE `site` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `type_alarme`
--

DROP TABLE IF EXISTS `type_alarme`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `type_alarme` (
  `type_alarme` varchar(30) NOT NULL,
  `seuil_warning` decimal(8,2) DEFAULT NULL,
  `seuil_critical` decimal(8,2) DEFAULT NULL,
  `unite` varchar(10) DEFAULT NULL,
  `description` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`type_alarme`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `type_alarme`
--

LOCK TABLES `type_alarme` WRITE;
/*!40000 ALTER TABLE `type_alarme` DISABLE KEYS */;
/*!40000 ALTER TABLE `type_alarme` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-23 14:59:09
