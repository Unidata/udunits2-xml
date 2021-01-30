# udunits2-xml

This project contains a tool for combining individual UDUNITS-2 xml unit definition files into a single xml document.
Each combined xml file is licensed under the terms of the UDUNITS-2 library, as outlined in the [UDUNITS-2 Copyright](https://github.com/Unidata/UDUNITS-2/blob/master/COPYRIGHT).
The combined xml file and its associated copyright file are then published and made publicly accessible.
The most recent version of the combined xml file and copyright file are available at:

* https://docs.unidata.ucar.edu/thredds/udunits2/current/udunits2_combined.xml
* https://docs.unidata.ucar.edu/thredds/udunits2/current/UDUNITS-2_COPYRIGHT

Specific versions are available using the following pattern:

* https://docs.unidata.ucar.edu/thredds/udunits2/<version>/udunits2_combined.xml
* https://docs.unidata.ucar.edu/thredds/udunits2/<version>/UDUNITS-2_COPYRIGHT

This code runs nightly to check for new releases of `udunits-2` and depends on tagged releases in the [official udunits-2 repository](https://github.com/unidata/udunits-2).
