# Convert macroalgae intertidal field data to DwC-A --> THIS WILL HAVE TO BE REWRITTEN FOR THE EOV FORMAT
library(readxl)
library(obistools)
library(reshape2)
library(tidyverse)
library(readr)
library(lubridate)
library(sf)
library(rnaturalearth)
library(rnaturalearthdata)
library(Hmisc)


# Load the data using readxl::read_excel
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 1) {
  stop("No input file provided", call. = FALSE)
}

input_file <- args[1]
output_dir <- args[2]
mag_int <- readxl::read_excel(input_file)
out_dir <- dirname(input_file)
names(mag_int)

##########  Event core ##########
event <- mag_int[,c(2:6,8:10,12:21,35:38)]

# Rename some columns to match with Darwin Core term
event <- event %>%
  rename(parentEventID = eventParentID,
         eventDate = `date (YYYY-MM-DDTHH-MM-SS)`,
         maximumDepthInMeters = `bottomDepth (m)`,
         locality = site
         ) %>%
  mutate(minimumDepthInMeters = 1.8) 

# Need to add the extra rows for the parent events
#first add the dates to the parentEvents
date_lookup <- tibble(
  parentEventID = c("Gelatinous_Gotland_Ajkesviken", "Gelatinous_Gotland_Burgsvik", 
                    "Gelatinous_Gotland_Fårösund", "Gelatinous_Gotland_Klintehamn", 
                    "Gelatinous_Gotland_Lausviken", "Gelatinous_Gotland_Vägumeviken"),
  eventDate = c("2022-08-17/2022-08-18", "2022-08-14/2022-08-15", 
                "2022-08-25/2022-09-12", "2022-08-16/2022-08-24", 
                "2022-09-14/2022-09-16", "2022-09-06/2022-09-07")
)
parentevents <- event %>%
  mutate(eventDate = str_sub(eventDate, 1, 10)) %>%     # Trim the date
  select(parentEventID, locality, country, year, samplingDevice,transectLength, transectLengthUnit) %>%
  distinct(parentEventID, .keep_all = T) %>%                # Keep one per parent
  left_join(date_lookup, by = "parentEventID") %>% 
  mutate(
    eventID = parentEventID,
    parentEventID = "",
    samplingDevice = "GoPro camera",
    transectLength = 55,
    transectLengthUnit = "m",
    country = "Sweden",
    eventDate = c("2022-08-17/2022-08-18","2022-08-14/2022-08-15", "2022-08-25/2022-09-12", 
                  "2022-08-16/2022-08-24", "2022-09-14/2022-09-16", "2022-09-06/2022-09-07")
  ) %>%
  select(year, parentEventID, eventID, eventDate, locality, country, 
         samplingDevice, transectLength, transectLengthUnit
         )

event<-bind_rows(parentevents,event)%>%
  mutate(across(everything(), ~ ifelse(is.na(.), "", as.character(.)))) #make sure the NAs are just blanks

event <- event %>%
  mutate(samplingProtocol = "camera tow | Luskow et al. 2025. https://doi.org/10.3390/jmse13050852",
         type = "Event",
         modified = lubridate::today(),
         language = "en",
         license = "https://creativecommons.org/licenses/by/4.0/", # use CC-BY license
         geodeticDatum = "WGS84",
         countryCode = "SE",
         stateProvince = "Gotland",
         locationID = "http://marineregions.org/mrgid/22248",
         waterBody = "Baltic Sea", 
         habitat = "seagrass") 
         

##########   Create Occurrence core ##########  
# This table will have all the information about the species that were observed 
# & associated sampling data
occ <- mag_int[,c(6,22:34,39,40)] #exclude irrelevant columns

occ <- occ %>%
  rename(#eventDate = `date (YYYY-MM-DDTHH-MM-SS)`,
         recordedBy = `dataCollectorName(s)`,
         identifiedBy = `name(s)OfPerson(s)WhoAssignedIdentification`,
         #maximumDepthInMeters = `bottomDepth (m)`,
         basisOfRecord = typeOccurrence,
         vernacularName = commonName,
         #locality = site
         ) %>%
  mutate(
    modified = lubridate::today(),
    language = "en",
    license = "https://creativecommons.org/licenses/by/4.0/", # used CC-BY license
    identifiedByID = "https://orcid.org/0000-0002-2100-7012",
    occurrenceID = paste0(eventID, "_", sprintf("%03d", row_number())),
    organismQuantityType = "individual count",
    basisOfRecord = "HumanObservation"
  )

### Next would be taxon matching with WoRMS
# but it is already done correctly so no need to do here

##########  Create eMoF table ##########
# Unlike our source file, eMoF tables are in long format, instead of wide
# This means that instead of having columns for each measurement, they will be recorded in rows

#create a function to make life easier
create_emof_rows <- function(data,
                             value_col = NULL,
                             manual_value = NULL,
                             unit_col = NULL,
                             manual_unit = NULL,
                             measurement_type,
                             type_id = "",
                             unit_id = "",
                             val_id = "") {
  
  # Sanity check
  if (is.null(value_col) && is.null(manual_value)) {
    stop("You must provide either 'value_col' or 'manual_value'.")
  }
  
  # Check for presence of eventID and occurrenceID
  df <- data.frame(eventID = if ("eventID" %in% names(data)) data$eventID else "",
                   occurrenceID = if ("occurrenceID" %in% names(data)) data$occurrenceID else "")
  
  # Handle measurementValue
  if (!is.null(value_col)) {
    df$measurementValue <- data[[value_col]]
    df <- df %>% filter(!is.na(measurementValue))
  } else {
    df$measurementValue <- manual_value
  }
  
  # Handle measurementUnit
  if (!is.null(unit_col)) {
    df$measurementUnit <- data[[unit_col]][!is.na(data[[value_col]])]
  } else if (!is.null(manual_unit)) {
    df$measurementUnit <- manual_unit
  } else {
    df$measurementUnit <- ""  # fallback default
  }
  
  # Add the other columns
  df <- df %>%
    mutate(
      measurementType = measurement_type,
      measurementTypeID = type_id,
      measurementUnitID = unit_id,
      measurementValueID = val_id
    )
  
  return(df)
}

surface_temp <- create_emof_rows(
  data = event,
  value_col = "surfaceTemperature",
  manual_unit = "degrees Celsius",
  measurement_type = "Sea surface temperature",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/TEMPPP01/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/UPAA/"
)

bott_temp <- create_emof_rows(
  data = event,
  value_col = "bottomTemperature",
  manual_unit = "degrees Celsius",
  measurement_type = "Sea bottom temperature",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/TEMPPP01/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/UPAA/"
)

translen <- create_emof_rows(
  data = event %>%
    filter(!str_detect(eventID, "_[A-Z][0-9]+$")), #exclude child events
  value_col = "transectLength",
  manual_unit = "metres",
  measurement_type = "length of sampling track",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/LENTRACK/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/ULAA/"
) #need to delete the extras

habitat <- create_emof_rows(
  data = event %>%
    filter(!str_detect(eventID, "_[A-Z][0-9]+$")), #exclude child events
  value_col = "habitat",
  #manual_unit = "metres",
  measurement_type = "Description of habitat by classification to a term from NERC M24 collection Marine Habitat Classification for Britain and Ireland Version 97.06",
  type_id = "http://vocab.nerc.ac.uk/collection/M24/current/",
  val_id = "http://vocab.nerc.ac.uk/collection/M24/current/LSLMSZOS/"
)

windir <- create_emof_rows(
  data = event,
  value_col = "windDirection",
  manual_unit = "degrees",
  measurement_type = "wind direction",
  type_id = "https://vocab.nerc.ac.uk/collection/P01/current/EGTDZZ01/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/UAAA/"
)

windsp <- create_emof_rows(
  data = event,
  value_col = "windSpeed",
  unit_col = "windSpeedUnit",
  measurement_type = "wind speed",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/EWSBZZ01/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/UVAA/"
)

sampproto <- create_emof_rows(
  data = event %>%
    filter(!str_detect(eventID, "_[A-Z][0-9]+$")), #exclude child events
  value_col = "samplingProtocol",
  #unit_col = "",
  measurement_type = "Description of sampling method",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/DSSPMT01/",
  val_id = ""
) 

sampdevice <- create_emof_rows(
  data = event %>%
    filter(!str_detect(eventID, "_[A-Z][0-9]+$")), #exclude child events
  value_col = "samplingDevice",
  #unit_col = "",
  measurement_type = "Name of sampling instrument",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/NMSPINST/",
  val_id = ""
) 

sampdevice2 <- create_emof_rows(
  data = event %>%
    filter(!str_detect(eventID, "_[A-Z][0-9]+$")), #exclude child events
  manual_value = "ProDSS Multiparameter Digital Water Quality Meter",
  #unit_col = "",
  measurement_type = "Name of sampling instrument",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/NMSPINST/",
  val_id = ""
)

estVol <- create_emof_rows(
  data = event,
  value_col = "estimatedVolume",
  unit_col = "estimatedVolumeUnit",
  measurement_type = "estimated volume sampled by computation",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/VOLFDGDT/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/MCUB/"
)

abund <- create_emof_rows(
  data = occ,
  value_col = "abundance",
  unit_col = "abundanceUnit",
  measurement_type = "abundance per cubic metre",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/SDBIOL01/",
  unit_id = "http://vocab.nerc.ac.uk/collection/P06/current/UPMM/"
)

count <- create_emof_rows(
  data = occ,
  value_col = "organismQuantity",
  unit_col = "organismQuantityType",
  measurement_type = "organism count",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/OCOUNT01/",
  unit_id = ""
)
lifestage <- create_emof_rows(
  data = occ,
  value_col = "lifeStage",
  #unit_col = "",
  measurement_type = "Development stage of biological entity specified elsewhere",
  type_id = "http://vocab.nerc.ac.uk/collection/P01/current/LSTAGE01/",
  #unit_id = ""
  val_id = "https://vocab.nerc.ac.uk/collection/S11/current/S1129/"
)

# Bind all the measurements together into one file   
emof <- rbind(surface_temp, bott_temp, translen, windir, windsp, habitat, 
                  sampproto, sampdevice, sampdevice2, estVol, abund, count, lifestage)
head(emof)

# save the file!
emof_file <- file.path(output_dir, paste0("emof_", lubridate::today(), ".csv"))
readr::write_excel_csv(emof, emof_file)


##########  Clean up Occ ##########  
#I'm doing this manually to put the columns in a specific order I like
eventcore <- event[c("parentEventID","eventID", "year", "eventDate","decimalLatitude",
                    "decimalLongitude","country", "countryCode", "stateProvince", "locationID",
                    "locality", "waterBody", "samplingDevice", "samplingProtocol",
                    "maximumDepthInMeters", "minimumDepthInMeters", "habitat","type",  
                    "modified", "language", "license", "geodeticDatum" )] 

occurrence <- occ[c("eventID","occurrenceID", "scientificName", "scientificNameID",
                    "vernacularName", "basisOfRecord", "occurrenceStatus",
                    "organismQuantity", "organismQuantityType","lifeStage","recordedBy",
                    "identifiedBy", "identifiedByID","modified", "language", 
                    "license" )] 

event_file <- file.path(output_dir, paste0("event_", lubridate::today(), ".csv"))
readr::write_excel_csv(eventcore, event_file)
occ_file <- file.path(output_dir, paste0("occurrence_", lubridate::today(), ".csv"))
readr::write_excel_csv(occurrence, occ_file)


##########  Quick QC checks ########## 
# obistools::check_fields(eventcore) #no errors
# obistools::check_fields(occurrence) #no errors
# obistools::plot_map_leaflet(eventcore) #looks okay
# obistools::check_depth(eventcore, report=TRUE) #some depths non matching but doesn't look too extreme
# obistools::check_onland(eventcore,report=TRUE) #no errors
# obistools::check_extension_eventids(eventcore, occurrence, field="eventID") #no errors
# obistools::check_extension_eventids(eventcore, emof, field="eventID") #no errors
# obistools::check_extension_eventids(occurrence, emof, field="occurrenceID") #errors not applicable
# obistools::check_eventdate(eventcore) #errors not applicable


# Hmisc::describe(eventcore) #nothing unexpected missing per variable
# options(grType='plotly')
# e<-Hmisc::describe(eventcore)
# p<-plot(e)
# p[[1]]; p[[2]] # quick visual look at the variables if anything stands out

# Hmisc::describe(occurrence) #nothing missing per variable
# options(grType='plotly')
# o<-Hmisc::describe(occurrence)
# p<-plot(o)
# p[[1]]; p[[2]]
# #one last check in case we missed anything
# obistools::report(occurrence) #all okay

