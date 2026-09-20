@echo off
set MAVEN_HOME=C:\tools\apache-maven-3.9.6
set PATH=%MAVEN_HOME%\bin;%PATH%
mvn.cmd package -q
