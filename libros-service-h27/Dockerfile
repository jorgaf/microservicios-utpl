# ---------- Etapa 1: compilar con Maven + JDK 27 (Helidon 27 exige Java 27) ----------
FROM maven:3.10-eclipse-temurin-27 AS build
WORKDIR /build

# Primero solo el pom: Docker cachea las dependencias mientras el pom no cambie
COPY pom.xml .
RUN mvn -B -q dependency:go-offline

COPY src ./src
RUN mvn -B -q package -DskipTests

# ---------- Etapa 2: imagen final, solo JRE (más liviana) ----------
FROM eclipse-temurin:27-jre
WORKDIR /app

COPY --from=build /build/target/libros-service.jar ./
COPY --from=build /build/target/libs ./libs

EXPOSE 8081
CMD ["java", "-jar", "libros-service.jar"]
