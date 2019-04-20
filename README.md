# udunits2-xml

This project contains a tool for combining individual udunits-2 xml unit definition files into a single xml document.

The resulting file is then published on the Unidata artifacts server and made publicly available at

`https://docs.unidata.ucar.edu/thredds/udunits2/<version>/udunits2_combined.xml`

Each combined xml file is licensed under the terms of the UDUNITS-2 library, as outlined in the UDUNITS-2 Copyright.
A versioned copy of the copyright is available at:

`https://docs.unidata.ucar.edu/thredds/udunits2/<version>/UDUNITS-2_COPYRIGHT`

For example, the combined xml file for version `v2.2.27.6` can be found at:

https://docs.unidata.ucar.edu/thredds/udunits2/2.2.27.6/udunits2_combined.xml

and the associated copyright at:

https://docs.unidata.ucar.edu/thredds/udunits2/2.2.27.6/UDUNITS-2_COPYRIGHT

The most recent version, and copyright, will be made available at:

https://docs.unidata.ucar.edu/thredds/udunits2/current/udunits2_combined.xml
https://docs.unidata.ucar.edu/thredds/udunits2/current/UDUNITS-2_COPYRIGHT

This code runs nightly to check for new releases of `udunits-2` and depends on tagged releases in the [official udunits-2 repository](Unidata/udunits-2).
