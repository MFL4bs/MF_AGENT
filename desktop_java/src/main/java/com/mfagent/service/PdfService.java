package com.mfagent.service;

import com.itextpdf.io.image.ImageDataFactory;
import com.itextpdf.kernel.colors.ColorConstants;
import com.itextpdf.kernel.colors.DeviceRgb;
import com.itextpdf.kernel.geom.PageSize;
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.layout.Document;
import com.itextpdf.layout.borders.SolidBorder;
import com.itextpdf.layout.element.*;
import com.itextpdf.layout.properties.*;
import com.mfagent.model.Invoice;
import com.mfagent.model.InvoiceItem;
import com.mfagent.util.EnvConfig;

import java.io.File;
import java.nio.file.Path;

/**
 * Generación de facturas PDF con iText 8.
 * Equivalente a _generate_pdf() en app.py (ReportLab → iText)
 *
 * Incluye: logo, encabezado empresa, datos cliente, tabla de productos, firmas.
 */
public class PdfService {

    private static final DeviceRgb ACCENT2  = new DeviceRgb(0x1B, 0x6C, 0xA8);
    private static final DeviceRgb SIDEBAR  = new DeviceRgb(0xED, 0xE8, 0xE3);
    private static final DeviceRgb BG       = new DeviceRgb(0xF5, 0xF0, 0xEB);
    private static final DeviceRgb TEXT     = new DeviceRgb(0x1F, 0x29, 0x37);
    private static final DeviceRgb BORDER   = new DeviceRgb(0xD1, 0xCB, 0xC4);
    private static final DeviceRgb SUCCESS  = new DeviceRgb(0x16, 0xA3, 0x4A);

    public void generate(Invoice invoice, String outputPath) throws Exception {
        String logoPath    = EnvConfig.get("WATERMARK_IMAGE", "MF_LABS.png");
        String bizName     = EnvConfig.get("BUSINESS_NAME", "Mi Empresa");
        String bizPhone    = EnvConfig.get("BUSINESS_PHONE", "");
        String bizEmail    = EnvConfig.get("BUSINESS_EMAIL", "");
        String bizAddress  = EnvConfig.get("BUSINESS_ADDRESS", "");
        String firma1      = EnvConfig.get("FIRMA1_LABEL", "Firma Empresa");
        String firma2      = EnvConfig.get("FIRMA2_LABEL", "Firma Cliente");
        String firma1Img   = EnvConfig.get("FIRMA1_IMAGE", "");
        String firma2Img   = EnvConfig.get("FIRMA2_IMAGE", "");

        PdfWriter writer = new PdfWriter(outputPath);
        PdfDocument pdf  = new PdfDocument(writer);
        Document doc     = new Document(pdf, PageSize.A4);
        doc.setMargins(42, 56, 56, 56);

        // ── Encabezado: logo | nombre empresa | datos factura ─────────────────
        Table header = new Table(UnitValue.createPercentArray(new float[]{15, 55, 30}))
                .useAllAvailableWidth();

        // Logo
        Cell logoCell = new Cell().setBorder(null);
        if (new File(logoPath).exists()) {
            try {
                Image logo = new Image(ImageDataFactory.create(logoPath))
                        .setWidth(70).setHeight(70);
                logoCell.add(logo);
            } catch (Exception ignored) {}
        }
        header.addCell(logoCell);

        // Nombre empresa
        Cell bizCell = new Cell().setBorder(null).setTextAlignment(TextAlignment.CENTER);
        bizCell.add(new Paragraph(bizName)
                .setBold().setFontSize(14).setFontColor(ACCENT2));
        if (!bizAddress.isEmpty()) bizCell.add(new Paragraph(bizAddress).setFontSize(9).setFontColor(TEXT));
        if (!bizPhone.isEmpty())   bizCell.add(new Paragraph("Tel: " + bizPhone).setFontSize(9).setFontColor(TEXT));
        if (!bizEmail.isEmpty())   bizCell.add(new Paragraph(bizEmail).setFontSize(9).setFontColor(TEXT));
        header.addCell(bizCell);

        // Datos factura
        Cell invCell = new Cell().setBorder(null).setTextAlignment(TextAlignment.RIGHT);
        invCell.add(new Paragraph("FACTURA").setBold().setFontSize(12).setFontColor(ACCENT2));
        invCell.add(new Paragraph("No: " + nvl(invoice.getInvoiceId())).setFontSize(9).setFontColor(TEXT));
        String fecha = invoice.getTimestamp() != null && invoice.getTimestamp().length() >= 10
                ? invoice.getTimestamp().substring(0, 10) : "";
        invCell.add(new Paragraph("Fecha: " + fecha).setFontSize(9).setFontColor(TEXT));
        header.addCell(invCell);

        header.setBorderBottom(new SolidBorder(ACCENT2, 1.5f));
        doc.add(header);
        doc.add(new Paragraph("\n").setFontSize(4));

        // ── Datos del cliente ─────────────────────────────────────────────────
        Table clientTable = new Table(UnitValue.createPercentArray(new float[]{25, 75}))
                .useAllAvailableWidth();

        Cell clientHeader = new Cell(1, 2)
                .add(new Paragraph("DATOS DEL CLIENTE").setBold().setFontSize(10).setFontColor(TEXT))
                .setBackgroundColor(SIDEBAR)
                .setBorder(new SolidBorder(BORDER, 0.5f))
                .setPadding(5);
        clientTable.addCell(clientHeader);

        addClientRow(clientTable, "Nombre:",    nvl(invoice.getCustomer(), "Consumidor final"));
        if (notEmpty(invoice.getCustomerPhone()))   addClientRow(clientTable, "Teléfono:",  invoice.getCustomerPhone());
        if (notEmpty(invoice.getCustomerAddress())) addClientRow(clientTable, "Dirección:", invoice.getCustomerAddress());
        if (notEmpty(invoice.getCustomerRfc()))     addClientRow(clientTable, "RFC:",       invoice.getCustomerRfc());

        doc.add(clientTable);
        doc.add(new Paragraph("\n").setFontSize(6));

        // ── Tabla de productos ────────────────────────────────────────────────
        Table prodTable = new Table(UnitValue.createPercentArray(new float[]{14, 42, 10, 17, 17}))
                .useAllAvailableWidth();

        for (String h : new String[]{"SKU", "Descripción", "Cant.", "Precio Unit.", "Subtotal"}) {
            prodTable.addHeaderCell(new Cell()
                    .add(new Paragraph(h).setBold().setFontSize(10).setFontColor(ColorConstants.WHITE))
                    .setBackgroundColor(ACCENT2)
                    .setBorder(new SolidBorder(BORDER, 0.5f))
                    .setPadding(6));
        }

        boolean odd = true;
        for (InvoiceItem item : invoice.getItems()) {
            DeviceRgb rowBg = odd ? new DeviceRgb(0xFD, 0xFA, 0xF7) : SIDEBAR;
            odd = !odd;
            prodTable.addCell(itemCell(item.getSku(), rowBg));
            prodTable.addCell(itemCell(item.getProductName(), rowBg));
            prodTable.addCell(itemCell(String.valueOf(item.getQuantity()), rowBg));
            prodTable.addCell(itemCell(String.format("$%,.2f", item.getUnitPrice()), rowBg)
                    .setTextAlignment(TextAlignment.RIGHT));
            prodTable.addCell(itemCell(String.format("$%,.2f", item.getSubtotal()), rowBg)
                    .setTextAlignment(TextAlignment.RIGHT));
        }

        // Fila total
        prodTable.addCell(new Cell(1, 3).setBorder(new SolidBorder(BORDER, 0.5f))
                .setBackgroundColor(BG).setPadding(6));
        prodTable.addCell(new Cell()
                .add(new Paragraph("TOTAL").setBold().setFontSize(11).setFontColor(TEXT))
                .setBackgroundColor(BG).setBorder(new SolidBorder(ACCENT2, 1.5f))
                .setPadding(6).setTextAlignment(TextAlignment.RIGHT));
        prodTable.addCell(new Cell()
                .add(new Paragraph(String.format("$%,.2f", invoice.getTotal()))
                        .setBold().setFontSize(11).setFontColor(SUCCESS))
                .setBackgroundColor(BG).setBorder(new SolidBorder(ACCENT2, 1.5f))
                .setPadding(6).setTextAlignment(TextAlignment.RIGHT));

        doc.add(prodTable);

        // Notas
        if (notEmpty(invoice.getNotes())) {
            doc.add(new Paragraph("\n").setFontSize(4));
            doc.add(new Paragraph("Notas: " + invoice.getNotes()).setFontSize(10).setFontColor(TEXT));
        }

        // ── Firmas ────────────────────────────────────────────────────────────
        doc.add(new Paragraph("\n\n").setFontSize(8));
        String line = "_".repeat(40);
        Table firmas = new Table(UnitValue.createPercentArray(new float[]{45, 10, 45}))
                .useAllAvailableWidth();

        // Fila con imagen o línea
        firmas.addCell(sigImageCell(firma1Img, line));
        firmas.addCell(new Cell().setBorder(null));
        firmas.addCell(sigImageCell(firma2Img, line));

        // Fila con etiqueta
        firmas.addCell(sigCell(firma1));
        firmas.addCell(new Cell().setBorder(null));
        firmas.addCell(sigCell(firma2));
        doc.add(firmas);

        doc.close();
    }

    private Cell itemCell(String text, DeviceRgb bg) {
        return new Cell()
                .add(new Paragraph(text != null ? text : "").setFontSize(10).setFontColor(TEXT))
                .setBackgroundColor(bg)
                .setBorder(new SolidBorder(BORDER, 0.5f))
                .setPadding(6);
    }

    private void addClientRow(Table t, String label, String value) {
        t.addCell(new Cell()
                .add(new Paragraph(label).setFontSize(10).setBold().setFontColor(TEXT))
                .setBorder(new SolidBorder(BORDER, 0.3f)).setPadding(4));
        t.addCell(new Cell()
                .add(new Paragraph(value).setFontSize(10).setFontColor(TEXT))
                .setBorder(new SolidBorder(BORDER, 0.3f)).setPadding(4));
    }

    private Cell sigImageCell(String imgPath, String fallbackLine) {
        Cell cell = new Cell().setBorder(null).setPaddingTop(4);
        if (imgPath != null && !imgPath.isEmpty() && new File(imgPath).exists()) {
            try {
                Image img = new Image(ImageDataFactory.create(imgPath))
                        .setMaxWidth(120).setMaxHeight(50)
                        .setHorizontalAlignment(HorizontalAlignment.CENTER);
                cell.add(img);
                return cell;
            } catch (Exception ignored) {}
        }
        // Fallback: línea
        cell.add(new Paragraph(fallbackLine).setFontSize(9).setFontColor(TEXT)
                .setTextAlignment(TextAlignment.CENTER));
        return cell;
    }

    private Cell sigCell(String text) {
        return new Cell()
                .add(new Paragraph(text).setFontSize(9).setFontColor(TEXT)
                        .setTextAlignment(TextAlignment.CENTER))
                .setBorder(null).setPaddingTop(4);
    }

    private String nvl(String s) { return s != null ? s : ""; }
    private String nvl(String s, String def) { return (s != null && !s.isEmpty()) ? s : def; }
    private boolean notEmpty(String s) { return s != null && !s.isEmpty(); }
}
