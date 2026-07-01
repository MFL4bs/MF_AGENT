// widgets/theme.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

const kBg      = Color(0xFFF5F0EB);
const kCard    = Color(0xFFFDFAF7);
const kAccent  = Color(0xFF1B6CA8);
const kText    = Color(0xFF1F2937);
const kSubtext = Color(0xFF6B7280);
const kSuccess = Color(0xFF16A34A);
const kWarning = Color(0xFFD97706);
const kDanger  = Color(0xFFDC2626);
const kBorder  = Color(0xFFD1CBC4);
const kSidebar = Color(0xFFEDE8E3);

ThemeData buildTheme() => ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: kBg,
      colorScheme: ColorScheme.light(
        primary: kAccent,
        secondary: kAccent,
        surface: kCard,
        error: kDanger,
      ),
      textTheme: GoogleFonts.interTextTheme(),
      appBarTheme: AppBarTheme(
        backgroundColor: kCard,
        foregroundColor: kText,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          color: kText,
        ),
      ),
      cardTheme: CardThemeData(
        color: kCard,
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: kAccent,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: kCard,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: kBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: kBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: kAccent, width: 2),
        ),
      ),
    );
