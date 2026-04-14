**Computerized maintenance**

**management system**

**WHO Medical device technical series**


```
WHO MEDICAL DEVICE TECHNICAL SERIES: TO ENSURE IMPROVED ACCESS, QUALITY AND USE OF MEDICAL DEVICES
```
```
HUMAN RESOURCES FOR MEDICAL
WHO MEDICAL DEVICE TECHNICAL SERIESDEVICES
```
```
DEVELOPMENT OF
MEDICAL DEVICE POLICIESPOLICIESCIE
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
Research and development
```
```
Medical devices
Assessment
```
```
Regulation
```
```
Management
```
```
PREMARKET APPROVAL
WHO MEDICAL DEVICE TECHNICAL SERIES WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEDICAL DEVICE REGULATIONS
```
```
HEALTH TECHNOLOGY ASSESSMENT OF
WHO MEDICAL DEVICE TECHNICAL SERIESMEDICAL DEVICES
```
```
Assessment
```
```
Regulation
```
```
NEEDS ASSESSMENT FOR MEDICAL
WHO MEDICAL DEVICE TECHNICAL SERIESDEVICES
```
```
Management
```
```
MEDICAL DEVICES BY CLINICAL
WHO MEDICAL DEVICE TECHNICAL SERIESPROCEDURES
```
```
Medical devices
```
```
MEDICAL DEVICE NOMENCLATURE
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEDICAL DEVICES BY HEALTH-CARE
FACILITIES
```
```
PROCUREMENT PROCESS
WHO MEDICAL DEVICE TECHNICAL SERIESRESOURCE GUIDE
```
```
MEDICAL DEVICE DONATIONS:
CONSIDERATIONS FOR SOLICITATION AND
WHO MEDICAL DEVICE TECHNICAL SERIESPROVISION
```
```
COMPUTERIZED MAINTENANCE
MANAGEMENT SYSTEM
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEDICAL EQUIPMENT MAINTENANCE
PROGRAMME OVERVIEW
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEDICAL EQUIPMENT INTRODUCTION TO
MANAGEMENTINVENTORY
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEDICAL DEVICESSAFE USE OF
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEASURING CLINICAL
WHO MEDICAL DEVICE TECHNICAL SERIESEFFECTINESS
```
```
DECOMMISSIONING MEDICAL DEVICES
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
SURVEILLANCE AND POST-MARKET
ADVERSE EVENT REPORTING
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
MEDICAL DEVICE INNOVATION
WHO MEDICAL DEVICE TECHNICAL SERIES
```
```
Research
and development
```
#### Publications available as of June 2011



# Computerized maintenance

# management system

**WHO Medical device technical series**


```
WHO Library Cataloguing-in-Publication Data
```
```
Computerized maintenance management system.
```
```
(WHO Medical device technical series)
```
```
1.Equipment and supplies. 2.Biomedical engineering. 3.Management information
systems. 4. Biomedical technology. I.World Health Organization.
```
```
ISBN 978 92 4 150141 5 (NLM classification: WX 147)
```
```
© World Health Organization 2011
All rights reserved. Publications of the World Health Organization can be obtained from
WHO Press, World Health Organization, 20 Avenue Appia, 1211 Geneva 27, Switzerland
(tel.: +41 22 791 3264; fax: +41 22 791 4857; e-mail: bookorders@who.int). Requests
for permission to reproduce or translate WHO publications – whether for sale or for
noncommercial distribution – should be addressed to WHO Press, at the above address
(fax: +41 22 791 4806; e-mail: permissions@who.int).
```
```
The designations employed and the presentation of the material in this publication do
not imply the expression of any opinion whatsoever on the part of the World Health
Organization concerning the legal status of any country, territory, city or area or of its
authorities, or concerning the delimitation of its frontiers or boundaries. Dotted lines on
maps represent approximate border lines for which there may not yet be full agreement.
```
```
The mention of specific companies or of certain manufacturers’ products does not imply
that they are endorsed or recommended by the World Health Organization in preference
to others of a similar nature that are not mentioned. Errors and omissions excepted, the
names of proprietary products are distinguished by initial capital letters.
```
```
All reasonable precautions have been taken by the World Health Organization to verify
the information contained in this publication. However, the published material is being
distributed without warranty of any kind, either expressed or implied. The responsibility
for the interpretation and use of the material lies with the reader. In no event shall the
World Health Organization be liable for damages arising from its use.
```
```
Design & layout: L’IV Com Sàrl, Villars-sous-Yens, Switzerland.
```
iv Computerized maintenance management system


## Contents


## Figures and tables

- Figures and tables
- Preface
   - Maintenance series and external guidance
   - Methodology
   - Defi nitions
- Acknowledgements
   - Declarations of Interests
- Acronyms and abbreviations
- Executive summary
- 1 Introduction
- 2 Purpose
- 3 CMMS structure
   - 3.1 Fields and tables
   - 3.2 Modules
      - 3.2.1 Equipment inventory module
      - 3.2.2 Spare parts inventory and management module
      - 3.2.3 Maintenance module
      - 3.2.4 Contract management module
   - 3.3 Screens and reports
- 4 Implementing CMMS
   - 4.1 Evaluation
   - 4.2 Selection
      - 4.2.1 Commercial packages
      - 4.2.2 Open source packages
      - 4.2.3 Locally developed packages
   - 4.3 Data collection
   - 4.4 Installation
   - 4.5 Confi guration and customization
   - 4.6 Data entry
   - 4.7 Training
   - 4.8 Follow-up and performance monitoring
   - 4.9 CMMS documentation and back up
- 5 Networking CMMS
- 6 Concluding remarks
- 7 References
- 8 Useful resources
- Appendix A Common fi elds included in medical equipment inventory
- Appendix B Sample CMMS screenshots
         - WHO Medical device technical series
- Appendix C Vendor specifi cation table
- Appendix D Request for proposal and vendor proposal sample content
- Appendix E Examples of CMMS vendors
- Appendix F Examples of open source CMMS providers
- Appendix G CMMS software design plan
- Figure 1. CMMS functionality fl owchart Figures and tables
- Table 1. Commonly used tables and related fi elds
- Figure 2. Table infrastructure for equipment inventory module
- Figure 3. Work order management fl ow chart
- Table 2. Types of reports that can be generated from a CMMS programme
- Figure 4. CMMS implementation fl ow chart
- Table 3. Advantages and disadvantages of a locally developed CMMS package
- Table 4. CMMS deployment solutions and related networking options


## Preface

Health technologies are essential for a functioning health system. Medical devices in
particular are crucial in the prevention, diagnosis, and treatment of illness and disease,
as well as patient rehabilitation. Recognizing this important role of health technologies,
the World Health Assembly adopted resolution in May 2007. The resolution covers
issues arising from the inappropriate deployment and use of health technologies, and
the need to establish priorities in the selection and management of health technologies,
specifi cally medical devices. By adopting this resolution, delegations from Member
States acknowledged the importance of health technologies for achieving health-related
development goals; urged expansion of expertise in the fi eld of health technologies, in
particular medical devices; and requested that the World Health Organization (WHO)
take specifi c actions to support Member States.

One of WHO’s strategic objectives is to “ensure improved access, quality and use of
medical products and technologies.” This objective, together with the World Health
Assembly resolution, formed the basis for establishing the Global Initiative on Health
Technologies (GIHT), with funding from the Bill & Melinda Gates Foundation. GIHT
aims to make core health technologies available at an affordable price, particularly
to communities in resource-limited settings, to effectively control important health
problems. It has two specifi c objectives:

- to challenge the international community to establish a framework for the
    development of national essential health technology programmes that will have a
    positive impact on the burden of disease and ensure effective use of resources;
- to challenge the business and scientifi c communities to identify and adapt innovative
    technologies that can have a signifi cant impact on public health.

To meet these objectives, WHO and partners have been working towards devising an
agenda, an action plan, tools and guidelines to increase access to appropriate medical
devices. This document is part of a series of reference documents being developed for
use at the country level. The series will include the following subject areas:

- policy framework for health technology
- medical device regulations
- health technology assessment
- health technology management
    › needs assessment of medical devices
    › medical device procurement
    › medical equipment donations
    › medical equipment inventory management
    › medical equipment maintenance
    › computerized maintenance management systems
- medical device data
    › medical device nomenclature
    › medical devices by health-care setting
    › medical devices by clinical procedures
- medical device innovation, research and development.

```
WHO Medical device technical series 3
```

```
These documents are intended for use by biomedical engineers, health managers,
donors, nongovernmental organizations and academic institutions involved in health
technology at the district, national, regional or global levels.
```
### Maintenance series and external guidance

```
Three documents in this technical series have been developed specifi cally to aid a health
facility or a national ministry of health to establish or improve a medical equipment
maintenance programme. The documents address medical equipment inventory
management, maintenance, and computerized maintenance management systems.
Each of these documents can be used as a stand-alone document, but together they
present all of the factors to consider when developing a medical equipment maintenance
programme. Furthermore, a six-volume comprehensive series of manuals for the
management of healthcare technology, known as the ‘How To Manage’ series, exists
for people who work for, or assist, health service provider organizations in developing
countries and are publicly available.^1
```
### Methodology

```
The documents in this series were written by international experts in their respective
fi elds, and reviewed by members of the Technical Advisory Group on Health Technology
(TAGHT). The TAGHT was established in 2009 to provide a forum for both experienced
professionals and country representatives to develop and implement the appropriate
tools and documents to meet the objectives of the GIHT. The group has met on three
occasions. The fi rst meeting was held in Geneva in April 2009 to prioritize which tools
and topics most required updating or developing. A second meeting was held in Rio de
Janeiro in November 2009 to share progress on the health technology management tools
under development since April 2009, to review the current challenges and strategies
facing the pilot countries, and to hold an interactive session for the group to present
proposals for new tools, based on information gathered from the earlier presentations
and discussions. The last meeting was held in Cairo in June 2010 to fi nalize the
documents and to help countries develop action plans for their implementation. In
addition to these meetings, experts and advisers have collaborated through an online
community to provide feedback on the development of the documents. The concepts
were discussed further during the First WHO Global Forum on Medical Devices in
September 2010. Stakeholders from 106 countries made recommendations on how
to implement the information covered in this series of documents at the country level.^2
```
```
All meeting participants and people involved in the development of these documents
were asked to complete a declaration of interest form, and no confl icts were identifi ed.
```
```
1 Available at http://www.healthpartners-int.co.uk/our_expertise/how_to_manage_series.html
2 First WHO Global Forum on Medical Devices: context, outcomes, and future actions is available at: http://www.who.int/medical_devices/gfmd_report_fi nal.pdf (accessed
March 2011)
```
4 Computerized maintenance management system


### Defi nitions

Recognizing that there are multiple interpretations for the terms listed below, they are
defi ned as follows for the purposes of this technical series.

**_Health technology:_** The application of organized knowledge and skills in the form of
devices, medicines, vaccines, procedures and systems developed to solve a health
problem and improve quality of life.^3 It is used interchangeably with health-care
technology.

**_Medical device:_** An article, instrument, apparatus or machine that is used in the
prevention, diagnosis or treatment of illness or disease, or for detecting, measuring,
restoring, correcting or modifying the structure or function of the body for some health
purpose. Typically, the purpose of a medical device is not achieved by pharmacological,
immunological or metabolic means.^4

**_Medical equipment:_** Medical devices requiring calibration, maintenance, repair, user
training, and decommissioning − activities usually managed by clinical engineers.
Medical equipment is used for the specifi c purposes of diagnosis and treatment of
disease or rehabilitation following disease or injury; it can be used either alone or in
combination with any accessory, consumable, or other piece of medical equipment.
Medical equipment excludes implantable, disposable or single-use medical devices.

3 World Health Assembly resolution WHA60.29, May 2007 (http://www.who.int/medical_devices/resolution_wha60_29-en1.pdf, accessed March 2011).
4 Information document concerning the defi nition of the term “medical device”. Global Harmonization Task Force, 2005 (http://www.ghtf.org/documents/sg1/sg1n29r162005.
pdf, accessed March 2011).

```
WHO Medical device technical series 5
```

## Acknowledgements

```
Computerized maintenance management system was developed under the principal
authorship of Iyad Mobarek, Technical Offi cer, World Health Organization (WHO) Country
Offi ce, Amman, Jordan and under the overall direction of Adriana Velazquez-Berumen,
WHO, Geneva, Switzerland as part of the Global Initiative on Health Technologies project
funded by the Bill & Melinda Gates Foundation.
```
```
The draft was reviewed by Matthew Baretich (Baretich Engineering), Jennifer Barragan
(WHO), Hashim El Zein (WHO), Victoria Gerrard (WHO), Adham Ismail (WHO), Joel
Nobel (ECRI Institute) and Frank Painter (University of Connecticut), and edited by Inis
Communication.
```
```
Special thanks to the director, heads of departments and staff of the Directorate of
Biomedical Engineering in Jordan for sharing their data and for their support. Thanks
are also due to all administrative staff at the WHO Country Offi ce in Jordan, namely
Miranda Shami, Julinda Kharabsheh, May Khoury, Samia Nawas, Banan Kharabsheh
and Layan Al Kindi, for their administrative support.
```
```
We would like to thank Aditi A Sharma for assistance in proofreading and Karina Reyes-
Moya and Gudrun Ingolfsdottir for administrative support throughout the development
of this document.
```
### Declarations of Interests

```
Confl ict of interest statements were collected from all contributors and reviewers to the
document development. No confl icts of interest were declared.
```
6 Computerized maintenance management system


## Acronyms and abbreviations

**CMMS** computerized maintenance management system
**IT** information technology
**HTM** health/health-care technology management
**IPM** inspection and preventive maintenance
**WHO** World Health Organization

```
WHO Medical device technical series 7
```

## Executive summary

```
As health facilities expand and the number of medical devices they depend on to
provide quality health care increases, a need to manage health-care technology more
effectively and effi ciently becomes evident. A computerized maintenance management
system (CMMS) is a tool that can improve overall medical equipment management at
the facility level. The information included in a CMMS varies depending on the individual
situation but always includes the medical equipment inventory and typically includes
information such as service history, preventive maintenance procedures, equipment
and performance indicators, and costing information.
```
```
A CMMS is made up of fi elds, tables and modules populated with data from the clinical
engineering or medical equipment department of a given facility. Using a CMMS, critical
data can be accessed, manipulated and analysed using user-friendly interfaces. Reports
can be generated from the system to help policy-makers reach decisions regarding
health technologies. However, it is important to take into consideration multiple factors
when deciding to adopt and develop a CMMS. Factors such as fi nancial and technical
resources are important when determining whether to purchase a commercial product,
use open-source software, or to develop a system locally. Implementation requires
proceeding through a number of phases that will allow the system to be planned
comprehensively. By completing this multistep process, the options for deployment will
be thoroughly evaluated; a suitable package will be selected, installed and customized;
data will be entered; and training on the CMMS will be provided.
```
```
For organizations with the appropriate resources to implement this tool, CMMS can be
very benefi cial. It is a highly fl exible tool that when properly implemented has the ability
to transform the management of medical equipment while also improving the availability
and functionality of the technology required to prevent, diagnose and treat illness.
```
8 Computerized maintenance management system


## 1 Introduction

Technology plays a key role in the effective
delivery of health care. The selection of
appropriate medical technology and the
organization of keeping that technology
in good working order fall under the remit
of health-care technology management
(HTM) programmes (1). HTM is often the
responsibility of the clinical engineering (or
medical equipment) department, which
tests, repairs and maintains diagnostic and
therapeutic clinical equipment to ensure
that it can be used safely and effectively (2).
Computerized maintenance management
systems (CMMS) have evolved to provide
support to HTM managers to maintain
medical equipment and monitor their
associated costs automatically.

A CMMS is a software package that contains
a computer database of information about
an organization’s maintenance operations.
In HTM, the CMMS is used to automate
the documentation of all activities relating
to medical devices, including equipment
planning, inventory management, cor-
rective and preventive maintenance
procedures, spare parts control, service
contracts, and medical device recalls and
alerts. The collected data can be analysed
and used for technology management,
quality assurance, work order control and
budgeting of medical devices (3).

The decision to automate a HTM system
or replace an existing CMMS depends on
the individual circumstances of the health
facility, including working procedures,
information technology (IT) infrastructure
and available budget. In order to
effectively assist in the management
and maintenance of medical equipment,
a CMMS must comprehensively meet
the needs of the user. Although major
vendors strive to develop a system that
universally meets the needs of all HTM

```
managers, no available system presents a
complete solution. Most, however, can be
customized to meet the specifi c needs of
the health facility. Alternatively, an IT fi rm
can be contracted to develop a CMMS
package tailored to local requirements. A
customized CMMS package is generally
more expensive but if well designed and
maintained will often produce a more
satisfactory solution that meets local
need.
```
```
A CMMS can be used to:
```
- standardize and harmonize infor-
    mation within a HTM programme;
- assist in the planning and monitoring
    of inspection and preventive main-
    tenance, and schedule and track
    repairs;
- monitor equipment performance
    indicators such as mean time
    between failures, down time and
    maintenance costs for individual
    or equipment groups of the same
    model, type or manufacturer;
- monitor clinical engineering staff
    performance indicators such as
    repeated repairs by the same staff
    member for the same problem,
    average down time associated with
    individuals, and productive work time
    for individuals or groups;
- generate reports that can be used
    to plan user training programmes
    based on equipment failure trends
    in certain departments or health
    facilities;
- host libraries of regulatory require-
    ments and safety information;
- generate the appropriate documen-
    tation for accreditation by regulatory
    and standard organizations;
- generate reports to assist in the
    monitoring and improvement of the

```
WHO Medical device technical series 9
```

```
productivity, effectiveness and per-
formance of HTM. Examples of these
reports include:
› the percentage of the cost of main-
tenance compared with the total
cost of equipment in the inventory;
› compliance with the inspection
and preventive maintenance pro-
gramme;
› mean productive working hours;
› identifi cation of medical equipment
affected by hazard and recall alerts.
```
```
Figure 1 presents a fl owchart of CMMS
functionality. The CMMS, whether com-
mercial or customized, can be used by
clinical engineers as a tool to complement
their current HTM programme and help
them fulfi l their departments particular
objectives. Effectively implementing a
good CMMS will improve patient care
through the effi cient management and
maintenance of medical equipment to
ensure that it functions reliably.
```
```
Figure 1. CMMS functionality fl owchart
```
```
Adoption of CMMS
Selection/development of CMMS
Preliminary data input and testing
Final data input and implementation
```
```
Equipment reception
Delivery and installation
Acceptance
Training (service and operation)
```
```
Equipment operation
```
```
Warranty service (if available)
Maintenance
Down time monitoring
Local support evaluation
```
```
Service contract/in-house support
Maintenance
Down time monitoring
Spare parts managment
Performance of equipment and supplier
```
```
Evaluation (downtime and cost of support)
Equipment performance
Supplier/manufacturer performance
Provide recommendation (procurement,
decommissioning, donation, etc.)
```
```
Quality control (QC)
Performance indicators
Technical and administrative QC
```
```
Equipment
decommissioning or
replacement
```
10 Computerized maintenance management system


## 2 Purpose

The purpose of this document is to pro-
vide a tool to guide health-care workers,
particularly biomedical and clinical engi-
neers, in adopting and implementing a
computerized method of managing their
maintenance system. It is specifi cally
aimed at those with the technical and
fi nancial resources to support such a sys-

```
tem. The reader will get an understanding
of the components of a CMMS and how
to select or develop a system that best
suits their needs. High-level managers
and policy-makers may wish to read this
document to further their understanding
of managing medical equipment and to
enable informed decision-making.decision-madecision-making.
```
```
WHO Medical device technical series 11
```

## 3 CMMS structure

```
A CMMS package integrates all medical
equipment services into a database
made up of fi elds, tables, modules and
screens. The following section gives a
brief introduction to this basic structure,
which can be used by HTM managers to
help choose or develop a system that is
suitable for their needs.
```
### 3.1 Fields and tables

```
A fi eld is a single piece of information, for
example an ‘equipment serial number’.
A table is a collection of related fi elds,
for example an equipment location table
might be made up of the fi elds ‘building’,
‘department and ‘room’ where a piece of
equipment is stored.
```
```
To avoid long descriptive text, it is useful
to develop a comprehensive, consistent
and simple coding system for the various
activities of the database. A single code
is a fi eld, and a collection of fi elds can be
organized into tables. Coding of tables can
be developed for equipment inventory,
personnel, maintenance procedures
and equipment locations. Commercial
CMMS packages normally have a set
of generic codes that can be adapted
or customized according to the needs
of the health facility. For ‘equipment
type’ coding, standard nomenclature
such as the Universal Medical Device
Nomenclature System and the Global
Medical Device Nomenclature System
should be considered. Implementing
appropriate nomenclature can also
facilitate the management of alerts and
vigilance reports.
```
```
Appendix A provides a list of fi elds that are
commonly included in a CMMS inventory
for health technology management.
```
```
Commonly used tables with their related
fi elds are shown in Table 1.
```
### 3.2 Modules

```
A module is a collection of tables and
data screens. The inventory module, for
example, is made up of the ‘equipment
```
## Table 1. Commonly used tables and related fi elds

```
Table Fields
Equipment
type
```
- Equipment type
- Inspection and preventive
    maintenance (IPM) procedures
- IPM frequency
- Risk level
- Responsible staff
Equipment
model
- Model number
- Serial number
- Parts list
- Parts code and name
- IPM procedures
Manufacturer/
seller
- Manufacturer code and name
- Seller code and name
- Manufacturer email, telephone and
address
- Seller email, telephone and address
- Manufacturer contact name
- Seller contact name
Stores/spares • Store code and name
- Parts code and name
- Parts order number
Staff • Employee code
- Employee name
- Employee position
- Access level
- Training details
Maintenance • Inventory number
- Work order number
- Service provider
- Service engineer code
- Fault code and name
- IPM procedures
Health facility • Facility code and name
- Building code and name
- Department code and name
- Type of facility

12 Computerized maintenance management system


type’ table, the ‘manufacturer information’
table and the ‘equipment location’ table.
The following sections describe the basic
modules of a CMMS package.

#### 3.2.1 Equipment inventory module^1

The inventory module is the core of any
CMMS and the fi rst to be constructed. It
is therefore very important to include all
fi elds necessary for effective HTM. When
new equipment is added to the inventory,
the equipment is registered within the
CMMS database through a data entry
screen.

Figure 2 presents a basic table infras-
tructure for an equipment inventory
module. In this fi gure there are three
tables that contribute information to the
fi nal inventory list. It is common practice

1 Please refer to Introduction to medical equipment inventory management in this
technical series for more details on developing an inventory.

```
to use stored default values to build
inventory records for new equipment,
as it reduces entry time and avoids
human error. For example, the table
holding information about equipment
type includes pre-stored values such as
the relevant inspection and preventive
maintenance (IPM) procedures, risk
level and responsible staff for every type
of medical equipment. It is therefore
only necessary to enter the equipment
code of a new piece of equipment into
the equipment table and all pre-stored
values associated with this code will
be added to the inventory. Similarly,
the other areas illustrate default values
associated with the equipment model,
location of medical equipment and
inventory number, respectively. This
allows modules to be built with maximum
effi ciency and maintains data integrity
(3). Although an initial time investment
```
## Figure 2. Table infrastructure for equipment inventory module

```
Equipment type table
```
```
Equipment model table
```
```
Entered values
Equipment code and name
```
```
Stored values
```
```
IPM procedures
IPM frequency
Risk level
Staff responsible
```
```
Entered values
```
```
Manufacturer name and code
Equipment model number
```
```
Stored values
```
```
Safety responsibility
Parts list
Trained staff names and codes
```
```
Equipment location table
```
```
Entered values
```
```
Facility name and code
Building code
Department name and code
```
```
Stored values
```
```
Building default values
Trained operator
Peripheral store code
```
```
Equipment inventory module
```
```
Entered values
```
```
Inventory number (auto generated)
Installation date
Seller code and name
Accessories and software
Purchase order number (purchase price)
```
```
WHO Medical device technical series 13
```

```
is required to construct coding tables
before the inventory data can be added,
the long-term time and error savings are
signifi cant.
```
#### 3.2.2 Spare parts inventory and management module

```
The spare parts management module
is an extension of the inventory module
that tracks the spare parts related to
equipment and helps to maintain stock
levels.
```
```
Stocked parts include those that are com-
mon to a number of different pieces of
equipment such as fuses, wires, batteries
and basic electronic components, and
those parts that are more specifi c to a
particular model such as circuit boards,
power supplies, X-ray tubes and ultra-
sound probes. Fields in the spare parts
inventory might include:
```
- part description (name);
- stock (inventory) number;
- manufacturer’s name, serial and part
    number;
- link to equipment model;
- minimum stock level;
- current stock level;
- part storage location;
- price and date purchased.

```
Depending on the maturity of the system,
these data can be entered manually or by
scanning a part-specifi c barcode, which
populates the appropriate fi elds within
the database. The data can be used to
generate screens that:
```
- alert the user to minimum stock lev-
    els for particular parts;
- create reports regarding the frequen-
    cy of part replacement, which can
    help with predicting maintenance
    schedules and future stock levels;
- list all the parts required for certain
    pieces of equipment;
- report on the consumption of reused
    parts.

```
Some CMMS packages provide a fully
automated operation that includes all
phases of spare parts management from
procurement to delivery, acceptance
testing and use.
```
#### 3.2.3 Maintenance module^2

```
The maintenance module assists the user
of the CMMS programme to effectively
manage their maintenance schedule.
Figure 3 provides an overview of how
the CMMS integrates with a standard
maintenance system in a hospital.
As demonstrated in this figure, the
CMMS can be used for both planned
preventive maintenance and corrective
maintenance.
```
```
Planned preventive maintenance
With the appropriate inputs, the comput-
erized system can calculate when a piece
of equipment will require maintenance
and advise which parts might need to be
ordered and when. The package can also
monitor the maintenance process and
log when it has been completed. Fields
required for this module may include:
```
- equipment-specifi c inspection and
    preventive maintenance procedures;
- equipment-specifi c inspection and
    preventive maintenance schedule;
- frequency of equipment fault;
- estimated equipment running hours.

```
Corrective maintenance
When an equipment user reports a prob-
lem with a piece of equipment, the clinical
engineering department can log the fault
in the CMMS system. The programme
will automatically generate a work order
and allow the manager of the system to
assign an engineer to the job. The CMMS
programme can provide information
regarding workload, training and expertise
of individual engineers to assist with this
decision. If an initial evaluation of the fault
identifi es that a specifi c part is required
```
```
2 Please see Medical equipment maintenance programme overview in this
technical series for more information on planning, managing, and implementing
maintenance.
```
14 Computerized maintenance management system


```
to complete the job, the computerized
system can record this and provide the
appropriate ordering information about
the part. When the job is complete the
status of the equipment can be logged
in the system.
```
```
Whether preventive or corrective, priority
levels for the maintenance to be done
can be assigned with reference to the
equipment risk, the strategic value to
the health facility, and the availability of
back-up equipment. In addition, mainte-
nance work order forms can be generated
in electronic or paper format to include
the relevant maintenance procedures
required to complete the work order (3,4).
```
#### 3.2.4 Contract management module

```
The contract management module is
used to track all externally provided main-
tenance services. The main factors to
```
```
monitor are cost and performance of both
vendor and equipment.
```
```
If the medical equipment is under con-
tract, either through warranty, com-
prehensive service contracts or partial
support service contracts, the vendor is
required to provide technical support to
the equipment over an agreed period.
The CMMS programme can automati-
cally generate alerts addressed to vendors
when a piece of equipment is logged as
faulty or is scheduled for inspection and
preventive maintenance. The terms and
related costs of any contract should be
stored in the system for reference.
```
```
If possible, interfacing the CMMS pro-
gramme with the accounts department’s
IT system is useful. All payments to ex-
ternal vendors can then be approved
electronically through the main fi nancial
```
## Figure 3. Work order management fl ow chart

```
Equipment fault Clinical engineering dept. notifi ed
```
```
Equipment fault
logged on CMMS
```
```
IPM schedule Work order generated
```
```
Inventory
```
```
Equipment history
screen
```
```
Work order closed
```
```
IPM procedures
```
```
Pending work order
(IPM or corrective)
```
```
Work order manager
```
```
Assign service
provider
```
```
Reporting system
```
```
Spare parts order
manager
```
```
Stores manager
```
```
Parts received
```
```
Job execution
```
```
Job Completed?
```
```
Parts available?
```
```
Parts required to
complete job?
```
```
Yes
```
```
Yes Yes
```
```
No
No
```
```
No
```
```
CMMS
```
```
WHO Medical device technical series 15
```

```
IT system of the health institution. If this
is not possible, approval forms for com-
municating with the accounts department
could be printed from the CMMS.
```
### 3.3 Screens and reports

```
A screen allows the user to add, collect
and analyse data from a selection of
fields, tables and modules through a
user-friendly interface. For example, the
‘equipment history’ screen is a collection
of data from various modules summarizing
the HTM activity related to a certain piece
of equipment. It is the main feature of a
CMMS and includes information such as
the inventory details, service activities,
work order details, spare parts used and
associated costs, and recall information.
Screens can be used to generate reports
that will assist in monitoring the activities
```
```
related to the management of medical
equipment. This helps managers to
evaluate the overall performance of
their HTM system. Appendix B presents
screenshots from typical CMMS software,
including an equipment history screen.
```
```
As with other CMMS functions, the re-
ports generated can either be predefi ned
standards or be customized for a par-
ticular application or use. An easy-to-use
interface allows the user to select the
information they would like to extract
and analyse from the database. The data
generated can be exported into other
programmes for further evaluation or
presentation, such as Excel, Access and
Fox Pro.
```
```
Examples of the types of reports that can
be generated by CMMS are outlined in
Table 2.
```
```
Table 2. Types of reports that can be generated from a CMMS programme
```
```
Report type Examples
List • Lists of equipment by health facility, department or manufacturer
```
- Lists of faults caused by operators in a certain department or health facility
- Lists of work orders completed by specifi c clinical engineering personnel
- Lists of all stock received in the past month
Summary • Equipment-specifi c reports to monitor work done on a piece of equipment, record any down time
experienced and assess the general availability of the device
- Dashboard report, which gives an overview of how the HTM programme is running. Information
    presented might include key performance indicators such as mean time between failures, down time
    and response time
Activity • Maintenance activities for certain selected health facilities or departments
- Maintenance activities for a specifi c piece of equipment
Workfl ow • Corrective maintenance work orders
- Planned preventive maintenance schedule
- Individual staff activity with respect to work orders that need completing
- Upcoming inspections, parts replacements, upgrades, etc.
Human resources • Annual/monthly staff working hours
- Staff response time to work orders and time taken to diagnose fault
- Service provider details and working hours
Financial • Equipment life-cycle cost
- Cost of service ratio, i.e. maintenance cost against equipment value
Regulatory • Summary of medical device recalls
- Information related to equipment failures and adverse incident reports

16 Computerized maintenance management system


## 4 Implementing CMMS

Clinical engineering staff must be in-
cluded in the entire CMMS planning and
implementation process. Figure 4 sum-
marizes a basic seven-step process for
implementing a CMMS.

### 4.1 Evaluation

It is important to conduct a feasibility
study to evaluate and assess the need for
a CMMS. During this phase, a complete
analysis is conducted and the scope of
the system is defi ned. Decisions are made

```
regarding the function of the system, and
the data required to meet this function
are identifi ed (3,4,7). This analysis can
be used to develop a clear technical
specifi cation for the CMMS that includes
all mandatory and optional features. Other
factors to consider at this stage might
include the current IT infrastructure, the
structure of the existing HTM system,
the staff skill level, the number of health
facilities that will use the system, and the
level of staff buy-in (3). It is also useful to
identify any obstacles to implementing
the system that might be encountered.
```
## Figure 4. CMMS implementation fl ow chart

```
Phase 1
```
```
Evaluation
```
```
Phase 2
```
```
Selection
```
```
Phase 3
```
```
Data collection
```
```
Phase 4
```
```
Installation
Phase 5
```
```
Confi guration and
customization
```
```
Phase 6
```
```
Data Entry
```
```
Phase 7
```
```
Training
```
```
WHO Medical device technical series 17
```

### 4.2 Selection

```
An HTM programme may range from
fully paperless to fully automated using a
CMMS. Therefore, the amount of features
in a CMMS can vary and selection of
those features will be based on the
needs of the user, who may wish to fully
or perhaps only partially automate the
management system. Once specifi cations
for a system have been identifi ed, an
appropriate package can be selected. It
may be one that is commercially available,
customized to the health facility’s needs
or designed specifi cally for the user.
```
#### 4.2.1 Commercial packages

```
There are several commercial CMMS
packages on the market, offering a range
of features. Most commercial CMMS
include the option of a personal digital
assistant and barcode scanner to allow
for full automation of the HTM system.
Radio-frequency identifi cation systems
are also becoming more popular and may
soon be part of a typical CMMS package.
It is therefore important to ensure the
programme is sufficiently flexible to
accommodate the specific needs of
the clinical engineering department
in which it is to be used. Selecting a
CMMS package that is rigid and forces
the user to significantly modify their
existing workfl ow will give poor results. It
is therefore prudent to compare current
HTM procedures with those of the CMMS
being considered. Appendix C provides
a vendor specifi cations table that can
be used to guide the selection process.
In addition to these specifi cations, it is
important to consider vendor reputation
and experience in automation of HTM
programmes and the number of health
facilities that will be using the CMMS.
```
```
The fi nal and total cost of the CMMS is a
signifi cant factor when selecting a CMMS.
In addition to the start-up costs, hidden
```
```
charges must be taken into account,
such as annual licensing fees, extra data
storage fees, upgrade fees, password fees
and technical support costs. Whether
tailor-made or commercially purchased,
the vendor’s responsibilities during all
phases of CMMS implementation must
be clearly defined and documented.
Appendix D provides sample content
for a request for proposal and a vendor
proposal. A non-exhaustive list of CMMS
vendors is provided in Appendix E.
```
#### 4.2.2 Open source packages

```
There are a number of open source
CMMS packages developed by different
institutions or personnel. Appendix F
provides a list of such CMMS packages
and their websites. The general challenge
of open source CMMS is the lack of
technical support and updates and
hidden technical support charges.
```
#### 4.2.3 Locally developed packages

```
If no commercial package meets the
needs of the user, a CMMS can be de-
veloped locally by an internal software
development team or with a contractor. If
the decision is to go with an internal team,
it is important to recognize that a team of
professionals will be responsible for defi n-
ing the requirements for the application,
testing, and eventually maintaining and
updating the software. If such support
will not be available in the long term, it
is better to consider an external contrac-
tor or a commercial product. In either
case, during development, a signifi cant
amount of staff time is required for design
and testing of the system. Any additional
work expected of staff should be planned
with regard to their normal work activi-
ties. Once designed, the institution must
ensure that the source code is updated
and stored securely.
```
18 Computerized maintenance management system


In order to benefi t from the experiences
of others, a review of the literature on
locally and commercially produced
CMMS is best performed before locally
developing a package (3). Appendix G
presents a proposed sequence of software
design steps for the local development
of a CMMS. Once the basic design is
accomplished, the automated procedure
is operated with test data and the whole
design is improved according to feedback
obtained from system users. This process
is repeated for all activities; once all
activities are automated, the complete
system is put into operational testing until
all remarks have been considered and all
problems are solved.

The advantages and disadvantages of
locally developing a CMMS are outlined
in Table 3.

In general, the decision to develop a local
CMMS is justifi ed only when commercial
packages do not meet the specific
requirements of the health-care institution

```
and when major modifi cations to HTM
are required to implement commercial
systems.
```
### 4.3 Data collection

```
A comprehensive survey and analysis of
all available data should be conducted
before implementing the CMMS. This
information may already be available at
the health facility, but some may need to
be collected from other sources.
```
### 4.4 Installation

```
Before installing the system, a system
administrator is assigned who is
responsible for the technical maintenance
of the system and for managing data
security.
```
```
The CMMS can be implemented as a
complete system, by individual modules,
by equipment type or by location. This is
```
## Table 3. Advantages and disadvantages of a locally developed CMMS package

```
Advantages Disadvantages
The system is tailored to meet the exact needs of the
institution without requiring any modifi cation to the
functions and procedures of the department.
```
```
There are limitations with regard to testing the system and collecting
user feedback. In contrast, commercial packages are able to perform
complete professional testing before they are made available to clients.
In addition, they have access to a large user group and the ability to
hold conferences to gather user feedback.
The system may be modifi ed continuously according
to new operational needs.
```
```
Source code for locally developed CMMS is sometimes poorly written,
which makes the system slow.
The institution has full ownership of the source code
if properly written and updated.
```
```
Development time may be long compared with commercial packages.
```
```
New reports can be easily designed according to
requests from the clinical engineering department
or health facility managers.
```
```
The system is dependent on the IT personnel and other staff who
developed it. The knowledge might be lost when those staff members
leave the organization.
Staff are more familiar with the system since they
have participated in its development.
```
```
Recurrent costs must be paid to an individual, team of individuals, or
company to develop and regularly update the software.
```
Source: Cohen T et al.(2003) (3)

```
WHO Medical device technical series 19
```

```
the decision of the clinical engineering
department and will depend on the
resources available.
```
```
The software is installed on the health
facility server or on the individual user’s
personal computer. All other hardware
devices such as line printers and scanners
must also be installed and confi gured.
```
### 4.5 Confi guration and customization

```
Configuration and customization with
existing mechanisms and procedures are
performed before data entry. Confi guration
of the system could cover areas such as
simple workfl ow, access and security, and
user preferences. Customization refers
to the technical functional requirements
of the system including custom screens
and tables, facility-specifi c workfl ow and
additional data fi elds (3,8).
```
### 4.6 Data entry

```
This phase consists of initial data entry
of common fi elds such as equipment
model number, inventory code, human
resources, equipment locations, manu-
facturer information and nomenclature
classifi cations. User security levels and
associated passwords, access levels and
access types are also set at this stage
(3,8). It is benefi cial for clinical engineer-
ing staff to be assigned to populate the
database, as they are familiar with the
terms being used.
```
```
Complete functionality of the system can
be tested with one set of data. Functions
to be tested include the creation of main-
tenance requests, generation of work or-
ders, completion of work orders, ordering
of spare parts and generation of reports.
```
```
Data entry can be completed when the
CMMS is working as required (3,7).
```
### 4.7 Training

```
It is important that each staff member
of the clinical engineering department
is fully confi dent and familiar with all
functions of the CMMS. It is useful to
begin staff training in the early stages
of implementation to increase staff
buy-in and improve confidence. In
order to manage expectations, it is also
important that basic generic database
training is provided for key senior clinical
engineering staff. Specifi c user training
follows system installation and testing. If
other personnel such as clinicians and
nurses are expected to use the system,
additional training should be provided
for them. A periodic review to assess
and evaluate training needs is highly
recommended, as there is often a steep
learning curve when using such systems.
```
```
Most vendors provide comprehensive
manuals for their CMMS and a help menu
to enhance usability. Online help is also
available for some systems. It is worth
noting that the implementation of CMMS
is more effective if support is provided
in the local language; most commercial
CMMS packages are available with
support in a range of different languages.
```
### 4.8 Follow-up and performance monitoring

```
Continuous monitoring of the system is
conducted to ensure that it is directly
contributing to the improvement and
effective running of the HTM programme.
Elements to be monitored include:
```
- the system’s ability to effectively pro-
    duce all needed performance indica-

20 Computerized maintenance management system


```
tors for the HTM programme, such
as down time and inspection and
preventive maintenance compliance;
```
- evaluation of the speed of activities
    such as generation of reports and
    inputting of data;
- usability and user satisfaction (col-
    lected using a questionnaire).

In addition to this, large vendors hold
annual conferences where user feedback
is collected and analysed to make
improvements to their system.

### 4.9 CMMS documentation and back up

Clear, accurate and comprehensive docu-
mentation for all components of the sys-
tem, including full details of hardware,

```
software, operating procedures, upgrades
and backup policies, should be kept by the
clinical engineering department. For cus-
tomized packages the source code should
be documented and updated with every
upgrade to the system. Several CMMS
programmes use open source systems or
are delivered with the source code in order
to avoid problems of ownership and code
complications (3,7).
```
```
It is advisable to establish a periodic back-
up policy to protect data in the event of an
emergency or system crash. Automatic
back up to more than one storage media
can be used; if this is not possible, a daily
manual back up is suffi cient. In addition
to all back up and recovery policies, it
is advisable to use mirror-image servers
to enhance data security, if and when
available.
```
```
WHO Medical device technical series 21
```

## 5 Networking CMMS

```
Depending on the IT infrastructure avail-
able and the size of the clinical engi-
neering department, the CMMS can be
networked in a variety of ways. In general
there are two main deployment options:
```
```
the on-premise and the on-demand solu-
tions (5). Table 4 describes the features
of these solutions and the networking
options available for each.
```
## Table 4. CMMS deployment solutions and related networking options

```
Solution Description Features Networking options
On-premise CMMS installed and runs on
premises of health facility
```
- Customer responsible for the
    technology infrastructure
- Customer pays licensing fee to use
    and customize software
- Customer may customize
    features and functions to meet
    requirements
- Customer has full control of
    infrastructure and data
       - Standalone workstation base
          system, which is useful only in
          small single workshops at small
          hospitals
       - Local area network system within
          clinical engineering department
       - Deployment over Internet at
          customer’s site (self-hosted online
          solution)
       - Open architecture with integration
          to other applications on similar or
          different platforms
       - Built using standard Microsoft Web
          Technologies
On-demand Software As A Service (SAAS) • Vendor provides application
licence to multiple customers
- Infrastructure and application
    managed by vendor
- System delivered over Internet
- User does not maintain hardware
    or software
- Customer pays for access to
    application
       - 100% Internet-based application
          requiring no installation on
          client’s machines
       - Deployment over Internet (hosted
          online solution)
       - Open architecture with integration
          to other applications on similar or
          different platforms
       - Built using standard Microsoft Web
          Technologies
Customized SAAS Customizable version of SAAS

22 Computerized maintenance management system


## 6 Concluding remarks

Whether it is a commercially available
package or a custom-designed option,
a CMMS has several benefits. Much
less staff time is needed for data entry,
maintenance tracking and reporting; it
minimizes human errors; and it allows
more effective monitoring of performance
indicators and staff productivity (3,6,7). The
CMMS provides electronic documentation

```
of equipment inventories, tests, repairs,
maintenance and equipment histories. If
implemented correctly, it can be used as
an effective tool by health facilities and
their clinical engineering departments to
complement their existing programmes
and improve the overall management of
the technology, while also contributing to
the more effective delivery of health care.
```
```
WHO Medical device technical series 23
```

## 7 References

1. Cohen T. Computerized maintenance management system. _Journal of Clinical_
    _Engineering,_ 2001, 26:200–211.
2. _Duke University Health System, Clinical Engineering_. Durham, NC, Duke Univer-
    sity Health System Department of Clinical Engineering, 2010 (http://clinicalengi-
    neering.duhs.duke.edu/modules/ce_pols/index.php?id=1).
3. Cohen T et al. _Computerized maintenance management systems for clinical engi-_
    _neering._ Arlington, Association for the Advancement of Medical Instrumentation,
    2003.
4. Barta RA. A computerized maintenance management system’s requirements
    for standard operating procedures. _Biomedical Instrumentation and Technology,_
    2001, 35(1):57-60.
5. _On-demand or on-premise: Understanding the deployment options for your new_
    _business management system_ (White Paper). Richmond, Sage North America,
    2009.
6. ECRI Institute (http://www.ecri.org).
7. Non-published articles by the Directorate of Biomedical Engineering of the Jordan
    Ministry of Health (http://www.dbe.gov.jo).
8. Data available from Maintenance Connection CMMS (http://www.maintenance-
    connection.com/mcv18/online/mc_home.htm).

24 Computerized maintenance management system


## 8 Useful resources

_Medical equipment management manual._ Arlington, VA, Association for the Advancement
of Medical Instrumentation, 2005.

Cram N. Computerized maintenance management systems: a review of available
products. _Journal of Clinical Engineering,_ 1998, 23:147–223.

Kullolli I. Selecting a computerized maintenance management system. _Biomedical
Instrumentation & Technology,_ 2008, 42:276–278.

Mobarek I et al. Enhanced performance and cost-effective clinical engineering system
for Jordan. _Journal of Clinical Engineering,_ 2005, 30:42–55.

Mobarek I et al. Fully automated clinical engineering system. _Journal of Clinical
Engineering,_ 2006, 31:46–60.

Staker T. A paperless computerized management information system for clinical
engineering. In: Cohen T et al, eds. _Computerized maintenance management systems
for clinical engineering._ Arlington, VA, Association for the Advancement of Medical
Instrumentation, 2003.

Wickens CD, Sallie EG, Yili L. _An introduction to human factors engineering._ New York,
Addison-Wesley Educational Publishers, 1998.

```
WHO Medical device technical series 25
```

## Appendix A Common fi elds included in medical equipment inventory

```
Field Description
Equipment inventory number Unique number assigned by a health facility to identify individual pieces of equipment
Equipment description (type)
and class code
```
```
Code that describes equipment in terms of relevant nomenclature system
```
```
Manufacturer’s name and
CMMS-generated code
```
```
Name of manufacturer of equipment and code that identifi es the manufacturer
```
```
Model number Code assigned by manufacturer to identify equipment model
Manufacturer’s serial number Code assigned by manufacturer that helps to identify equipment during a recall; also used
to locate equipment if inventory number is removed
Current software revision Name of software device is running on; assists in identifi cation of devices affected by a
recall; also used to identify equipment that needs a software upgrade
Vendor (seller) name and code Name of vendor of equipment and code that identifi es the vendor
Location description and code Building, department or room where equipment is installed, and code that identifi es this
location
Purchase price Exact amount of money paid for equipment and currency used for payment
Installation date Date when equipment was offi cially accepted and put into operation by medical staff and
clinical engineers
Warranty expiration date Date warranty expires; usually indicated on purchase order
Inspection and preventive
maintenance procedure
reference
```
```
Code that assigns specifi c inspection and preventive maintenance procedure for equipment,
including frequency of procedure per year
```
```
Maintenance responsibility Name and code of institution or department, whether an external, central or peripheral
workshop or organization responsible for maintenance of equipment
Status fl ag Indicates current status of the equipment (e.g. operational, out of order, awaiting spares,
due for replacement)
Other customizable fi elds Fields relevant to individual technical management programme
```
26 Computerized maintenance management system


## Appendix B

Sample CMMS screenshots^1

1 Reproduced with permission from the ECRI Institute web site (6).

#### Equipment history

#### 

#### Work order

#### 

```
WHO Medical device technical series 27
```

## Appendix C Vendor specifi cation table

```
Vendors can fi ll in a table such as this one but may choose to include additional features.
Minimum requirements are fi lled in by the user based on their specifi c situation. Those
seen here are simply examples.
```
```
Technical specifi cation Minimum requirements Supplier specifi cations
Vendor information Please specify name, address and country of origin
```
```
Is vendor specialized in CMMS
dedicated to health technology?
```
```
Please answer yes or no
```
```
Name or version number of
CMMS
```
```
Required
```
```
Where marketed Please provide full list of countries, hospitals, etc.
```
```
Quality standards supported Please specify
```
```
Year fi rst sold
```
```
Please state year fi rst sold and locations
for:
```
- First sold CMMS version
- This offered version
User-friendly with minimal
learning curve

```
Required; please explain
```
```
Training support Required; please explain
```
```
Nomenclature system Required; please specify
```
```
Number of users Please specify maximum limit
```
```
Access groups/security levels Required
```
```
Document library HTML and document editor
```
```
Accounts/budgeting Preferred
```
```
Price
```
```
Please specify clearly your price, including
all components, such as annual subscription
fee and licence cost
Automated fi nancial system
interface
```
```
Preferred
```
```
Inventory management
```
- Inventory management module
- Barcode tracking
- Online recording and tracking

```
Spare parts management
module
```
- Inventory control
- Minimum stock order
- Spares order
- Costing
- Parts exchange

28 Computerized maintenance management system


**Technical specifi cation Minimum requirements Supplier specifi cations**

Work order module

- Work order manager
- Scheduling
- Priority
- Service charges (e.g. labour time,
    spares)
- Integrated fi elds
- Customized fi elds

Contract management Required

Project management module Required

Generate purchase orders Required

Work order request over the
Internet by clinical staff

```
Optional
```
Multisite asset tracking and
work orders

```
Required
```
Close work orders instantly
using a handheld personal
digital assistant/barcode
scanner

```
Preferred
```
Technical support 24 hours, 7 days a week

Remote diagnosis Required

System upgrades

- Please explain policy and cost
- Advantage given to free upgrades or
    cost included in annual fee or licence

Maintenance management

- Scheduling
- Inspection and preventive maintenance
    library (forms)
- Customizable forms

Equipment life-cycle
management

- Tracking of purchase
- Evaluation
- Auto-receiving
- Full history record of equipment

Operating systems Please specify

Integrated reporting system

- Run quick, standard, technical and
    managerial reports
- Create customizable reports

Invoice matching Optional

Automatic alerts and recalls Required

Create tasks and planned events Required

Print, email or fax reports Required

Database system Please specify

Considerations for local
environment

```
Local language, currency, calendar
```
```
WHO Medical device technical series 29
```

```
Technical specifi cation Minimum requirements Supplier specifi cations
```
```
Required deployment and
connection of CMMS
```
- Local-area network
- 100% Internet-based application
    requiring no installation on client’s
    machines
- Deployment over Internet (hosted
    online solution) or at customer’s site
    (self-hosted onsite solution)
- Open architecture with integration
    to other applications on similar or
    different platforms
- Scalable connection. (design and
    architecture to be used regardless of
    whether application has 10 or 10 000
    concurrent users?)
Network supported Please specify hardware and operating systems supported

```
Multiple site support Required
```
```
Use of SQL or other by CMMS Please answer yes or no
```
```
Updating mechanisms Please specify mechanisms used to prevent simultaneous or erroneous updating
```
```
Import and export utilities
available
```
```
Please specify
```
```
Other system features Please specify
```
30 Computerized maintenance management system


## Appendix D Request for proposal and vendor proposal sample content

The following is based on documents found on the ECRI Institute website (6). It is
intended as a reference only and should be modifi ed to fi t individual requirements.

### Request for proposal (RFP)

All software components of the CMMS supplied by the vendor shall be part of the
vendor’s normal currently produced CMMS product.

All other costs such as licensing fees for the use of the vendor’s software components
or database must be included within the quoted price of the CMMS or an annual fee.

All CMMS components provided according to the terms of this RFP shall be of the latest
production.

If the vendor plans to halt production of its CMMS referenced herein and to produce
improved models before the delivery date, the vendor shall immediately notify the user
in writing of this fact and provide the option of upgrading the purchase.

All support services must be provided by qualifi ed full-time employees working
exclusively for the vendor on a continuous basis, 24 hours a day, 7 days a week.

On-site training must be provided by a qualifi ed instructor of the vendor who is not a
sales representative. This training must be suffi cient to ensure optimum utilization of
the CMMS.

The order in which these selection criteria are listed is not necessarily indicative of
their relative importance. It is expected that any vendor submitting a proposal will
demonstrate extensive and substantial qualifi cations, capabilities and experience in
developing, installing and supporting the CMMS, including successful provision of the
same products and services to health institutions worldwide.

The user intends to select a vendor on the basis of the proposal received in response to
this RFP and any other information it obtains from other sources regarding the CMMS
and the vendor. Site visits to vendor installations may also be made by user staff. The
user reserves the right to make its fi nal decision independent of any or all of the above
factors.

```
WHO Medical device technical series 31
```

```
Proposals shall be delivered on or before: [date].
```
```
Offers shall be delivered to:
```
```
Attention of:
```
```
E-mail:
```
```
Telephone:
```
```
Fax:
```
```
Address:
```
```
The proposed installation date[s] for the CMMS is/are: [dd/mm/yyyy].
```
### Vendor proposal format

#### Price

```
The fi rst section of the proposal shall be a total price quotation including all system
components for the purchase, including installation, start-up, training, testing and
annual licensing fees of the CMMS.
```
```
Evaluation of the price shall be based on the total cost of CMMS over 10 years.
```
#### Installation and schedule

```
A proposed delivery and installation schedule for the CMMS shall be given, including
time required for installation, start-up, vendor and user acceptance testing. Both vendor
and user shall work together to install and operate the CMMS in pilot units identifi ed
by the user.
```
#### Payment

```
Proposed CMMS payment terms, including any cancellation fees and any alternatives
or offers that result in a cost saving to users must be clearly stated. Full prepayment at
the time of order placement, for example, is not acceptable to the user. Furthermore,
penalties for late or inadequate delivery, installation or training are included in the terms.
```
#### Substitution

```
The vendor shall supply at no extra cost the latest or any new version of the CMMS
introduced by the vendor after the award, but before delivery, that more suitably meets
the user’s requirements. The vendor should specifi cally address potential technical
differences.
```
#### Implementation plan

```
Vendors shall submit as part of the proposal the main elements of their implementation
plan. They are also expected to demonstrate their CMMS at the request of the user.
```
32 Computerized maintenance management system


#### Required IT infrastructure

The vendor shall provide a complete and detailed description of all IT requirements
(hardware and software) that will be required to install and operate the system.

#### Upgrades and enhancements

The vendor shall provide a copy of the vendor’s policy for newly developed versions
of the software, software modifi cations for improved performance and reliability, and
correction of design. The vendor should indicate whether such modifi cations, upgrades
and enhancements are no-charge items. Privilege shall be given to vendors with free
upgrades and enhancements.

#### Training

Vendors shall provide a detailed description of the training to be provided for clinical
engineering personnel specifi ed by the user. This could include a description of the
programme length and format, content, the qualifi cations of the instructors, and written
or electronic materials. The description should address the need for refresher training
and training for new users specifi ed by the user over the lifetime of the CMMS.

#### Operator manual

Vendors shall make available a fully descriptive operating manual online and on CD.

#### Technical support

A description of online, local or regional technical support capabilities, including the
number and qualifi cations of technical support staff, as well as their training, their base
locations, the locations of support staff, and approximate response time for emergency
(both during and outside of regular business hours), shall be included.

#### Annual subscription fees

A full description of annual subscription fees must be included. This includes the exact
period this covers, in addition to all terms, conditions and fees, system enhancements
and upgrades, software maintenance, technical support, software licence, and any
other factors that could be of interest to the user in evaluating the vendor’s proposal.
The price for each annual period and penalties for delayed response time to service
requests are clearly indicated.

```
WHO Medical device technical series 33
```

## Appendix E Examples of CMMS vendors

```
The following is a list of vendors and products offering CMMS software. This list is
not meant to be exhaustive. Inclusion on this list does not imply endorsement or
recommendation by WHO. It is meant only as a guide when searching for a database
that best suits your organization’s needs.
```
```
Vendor Website
Azzier http://www.azzier.com
```
```
Drawbase Software, Inc. http://www.drawbase.com
```
```
Eagle Technology, Inc. http://www.eaglecmms.com
```
```
ECRI Institute http://www.ecri.org.uk/ecriaims.htm
```
```
eMaint Enterprises, LLC http://www.emaint.com
```
```
EQ2, Inc. http://www.eq2.com
Facilities Technology
Group
```
```
http://www.factech.com
```
```
FM Works http://www.fmworks.com
Four Rivers Software
Systems
```
```
http://www.frsoft.com
```
```
GE Healthcare http://www.gehealthcare.com/euen/services/asset-management-solutions/asset_plus/index.html
```
```
ISES Corporation http://www.isescorp.com/services/operationsmaintenanceprogramming.aspx
```
```
Maintenance Connection http://www.maintenanceconnection.com
```
```
MicroMain Corporation http://www.micromain.com/
MPulse Maintenance
Software
```
```
http://www.mpulsesoftware.com
```
```
Nuvek, LLC http://www.vektr.com
PEAK Industrial
Solutions, LLC
```
```
http://www.cmms4hospitals.com
```
```
Phoenix Data Systems,
Inc.
```
```
http://www.goaims.com
```
```
Predictive Service http://www.predictiveservice.com
```
```
Simple Solutions FM http://www.simplesolutionsfm.com
St. Croix Systems
Corporation
```
```
http://www.stcroixsystems.com/asset_manager.aspx
```
```
Thinkage Ltd. http://www.mainboss.com
```
```
TISCOR http://www.tiscor.com
```
```
TMA Systems, LLC http://www.tmasystems.com
```
34 Computerized maintenance management system


## Appendix F Examples of open source CMMS providers

The following is a list of open source CMMS providers. This list is not meant to be
exhaustive. Inclusion on this list does not imply endorsement or recommendation by
WHO. It is meant only as a guide when searching for a database that best suits your
organization’s needs.

```
CMMS Website Notes
Aware http://www.pninc.com/maint/aware.htm Platform-independent
```
```
Facilities Desk http://www.manageengine.com/products/facilities-desk/index.html Windows XP, 2000, Vista, Linux
```
```
Maintenance Assistant http://www.maintenanceassistant.com Web base and other options
```
```
Maintenance Parts Bin http://www.nhuntsoftware.biz Windows 95/98/ME/XP/2000/NT
```
```
Maintenance Tracker http://www.mtrackcmms.com Windows XP, Win 98, MS Access 2002
```
```
Mantra http://www.bmstech.com/mantra/download.htm Windows XP/2000/NT4/9x/ME/Windows 3.1x/DOS
```
```
PLAMAHS http://www.healthpartners-int.co.uk/our_expertise/plamahs.html Windows 95 or later
```
```
WHO Medical device technical series 35
```

## Appendix G CMMS software design plan

```
HTM system
Activity 1
IPM
```
```
Activity 2
Corrective maintenance
```
```
Activity 3
Quality control
```
```
Activity n ...
```
```
Individual procedure steps
```
```
Consult clinical
engineers
```
```
Design screen cross-
referencing
```
```
Design data entry
screen
```
```
Design tables cross-
referencing
```
```
Assign primary and
secondary fi elds
```
```
Program fi elds
```
```
Design database tables
```
```
Determine fi elds
referred to in procedure
```
```
Program activities of
procedure
```
```
Program activities
fi elds
```
```
Create screen required
for activities
```
```
Determine procedure
activities
```
```
Establish follow-up
activities
```
```
Determine
personnel-
approval link
```
```
Determine
needed
approvals
```
```
Establish
security levels
```
```
Design report
screens
```
```
Determine
output data
```
```
Program report
fi elds
```
36 Computerized maintenance management system


**Department of Essential Health Technologies**
World Health Organization
20 Avenue Appia
CH-1211 Geneva 27
Switzerland
Tel: +41 22 791 21 11
E-mail: medicaldevices@who.int
[http://www.who.int/medical_devices/en/](http://www.who.int/medical_devices/en/)

```
ISBN 978 92 4 150141 5
```

