import os
import uuid
import json
from datetime import datetime
from docx import Document
from openai import OpenAI
import base64


def generate_family_report(data, images, api_key):
    """
    Genereert een familieverslag met behulp van de OpenRouter API.

    Parameters:
    - data: Een dictionary met de gegevens voor het verslag
    - images: Een lijst met geüploade afbeeldingspaden
    - api_key: De OpenRouter API-sleutel

    Returns:
    - Een tuple (verslag_tekst, bestandsnaam_docx)
    """
    # Converteer de afbeeldingen naar base64 voor de API
    image_descriptions = []
    for img_path in images:
        if os.path.exists(img_path):
            with open(img_path, 'rb') as img_file:
                file_extension = os.path.splitext(img_path)[1][1:].lower()
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                image_descriptions.append(f"![Afbeelding](data:image/{file_extension};base64,{img_base64})")

    # Bereid de input voor de AI voor
    prompt = f"""
    Schrijf een volledig familiestamboom onderzoeksverslag op basis van de volgende informatie:
    
    ONDERZOEKSVRAAG: {data.get('onderzoeksvraag', '')}
    DEELVRAGEN: {data.get('deelvragen', '')}
    
    INTERVIEWS:
    {data.get('interviews', '')}
    
    BRONNEN:
    {data.get('bronnen', '')}
    
    DOCUMENTEN EN BOEKEN:
    {data.get('documenten', '')}
    
    EXTRA NOTITIES:
    {data.get('notities', '')}
    
    Het verslag moet het volgende bevatten:
    1. Een inleiding met de onderzoeksvraag en deelvragen
    2. Een beschrijving van hoe het onderzoek is aangepakt
    3. De resultaten van het onderzoek, inclusief wat er is ontdekt
    4. Een conclusie die antwoord geeft op de onderzoeksvraag
    
    Schrijf dit als een samenhangend verhaal over de familiegeschiedenis, met een duidelijke structuur en hoofdstukken.
    Noem specifieke feiten, plaatsen, jaartallen, en personen die in de input worden genoemd.
    """

    # OpenRouter API aanroepen
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "familiegeschiedenisproject.com",
                "X-Title": "Familiegeschiedenis Project",
            },
            model="deepseek/deepseek-r1-zero:free",
            messages=[
                {"role": "system", "content": "Je bent een expert in familiestamboomonderzoek en geschiedschrijving. Je schrijft een uitgebreide onderzoek met alle data die je hebt gekregen. Je zoekt op het internet naar de gegeven bronnen en documenten."},
                {"role": "user", "content": prompt}
            ]
        )

        report_text = completion.choices[0].message.content

        # Maak een Word-document
        doc_path = create_word_document(data, report_text, images)

        return report_text, doc_path

    except Exception as e:
        print(f"Fout bij het genereren van het verslag: {e}")
        return f"Er is een fout opgetreden bij het genereren van het verslag: {str(e)}", None


def create_word_document(data, report_text, images):
    """Maakt een Word-document met het gegenereerde verslag en afbeeldingen"""
    doc = Document()

    # Titel
    doc.add_heading('Familiestamboom Onderzoeksverslag', 0)

    # Datum
    doc.add_paragraph(f"Gegenereerd op: {datetime.now().strftime('%d-%m-%Y %H:%M')}")

    # Onderzoeksvraag
    doc.add_heading('Onderzoeksvraag', 1)
    doc.add_paragraph(data.get('onderzoeksvraag', ''))

    # Verslag tekst
    doc.add_heading('Verslag', 1)
    for paragraph in report_text.split('\n\n'):
        if paragraph.strip():
            # Controleer op kopjes
            if paragraph.strip().startswith('#'):
                level = paragraph.count('#')
                doc.add_heading(paragraph.strip('#').strip(), level)
            else:
                doc.add_paragraph(paragraph)

    # Afbeeldingen toevoegen
    if images:
        doc.add_heading('Bijgevoegde afbeeldingen', 1)
        for img_path in images:
            if os.path.exists(img_path):
                try:
                    doc.add_picture(img_path, width=4000000)  # Breedte in EMU (ca. 10cm)
                    doc.add_paragraph(f"Afbeelding: {os.path.basename(img_path)}")
                except Exception as e:
                    doc.add_paragraph(f"Kon afbeelding {os.path.basename(img_path)} niet toevoegen: {str(e)}")

    # Sla het bestand op
    unique_id = uuid.uuid4().hex[:8]
    filename = f"familiestamboom_verslag_{unique_id}.docx"
    file_path = os.path.join('app/static/uploads', filename)
    doc.save(file_path)

    return filename


def generate_family_tree_data(data):
    """
    Genereert eenvoudige familierelaties uit de verstrekte gegevens
    voor visualisatie in een familiestamboom.
    """
    # Eenvoudige implementatie: extractie van namen en relaties
    # In een echte applicatie zou je hier een geavanceerder algoritme gebruiken

    interviews = data.get('interviews', '')
    bronnen = data.get('bronnen', '')
    documenten = data.get('documenten', '')

    all_text = f"{interviews} {bronnen} {documenten}"

    # Eenvoudige familierelaties uit de tekst halen
    family_data = {
        "name": "Familie Stamboom",
        "children": []
    }

    # Dit is een zeer eenvoudige implementatie
    # In een echte applicatie zou je hier NLP gebruiken of een beter algoritme
    names = extract_names_from_text(all_text)

    for name in names:
        family_data["children"].append({"name": name})

    return json.dumps(family_data)


def extract_names_from_text(text):
    """Zeer eenvoudige functie om mogelijke namen uit tekst te halen"""
    # Dit is een zeer eenvoudige implementatie die alleen werkt voor namen tussen dubbele quotes
    import re
    names = re.findall(r'"([^"]*)"', text)

    # Voeg enkele standaard familienamen toe als er geen werden gevonden
    if not names:
        names = ["Jan", "Maria", "Pieter", "Anna", "Willem"]

    return names[:10]  # Limiteer tot 10 namen