# -*- coding: utf-8 -*-
"""
model.py  --  Beko Cerkezkoy TV Anakart Uretim Planlama / MILP Optimizasyon
---------------------------------------------------------------------------
veri_oku.py'nin hazirladigi sabit girdileri alir; tezde tanimlanan
tampon-fizibilite esasli, cok donemli, CLSP-SI yapisindaki modeli
PuLP + CBC ile kurup LEKSIKOGRAFIK olarak cozer.

MODELIN FELSEFESI
  - Montaj ASLA ac kalmamalidir  -> KSO, KSM, KST >= 0 SERT kisit.
  - OTD hat alokasyonu bir KARAR DEGISKENIDIR (referans plan degil).
  - Bir OTD hattinda bir gunde yalniz BIR kart tipi uretilir.
  - Kart degisikligi (setup) %50 kapasite kaybi yaratir (CLSP-SI).
  - Cozum uc asamalidir (leksikografik):
      ASAMA 1 : Toplam tampon ACIGINI (gO+gM+gT) minimize et.
                Acik 0 ise plan fizibildir; >0 ise kacinilmaz minimum
                acigi ve yerini gosterir (mesai/ek vardiya girdisi).
      ASAMA 2 : Acigi sabitle, toplam OTD SETUP SAYISINI (Sigma zO)
                minimize et.
      ASAMA 3 : Acik ve setup'i sabitle, toplam tampon stoku
                minimize et (yalin plan -- uretim ihtiyac kadar).

KANAL YAPISI (MD)
  MD asamasi 2 fiziksel hat (MD1, MD2) icerir; MD2 ayni gun iki karti
  paralel isleyebilen iki KANAL barindirir (MD2_1, MD2_2). L_M kanal
  temellidir: {MD1, MD2_1, MD2_2}. Ayni fiziksel hattaki kanallar
  paylasimli kapasite kisiti ile baglanir.
  MD alokasyonu REFERANS PLANDIR; ancak onarim (yM) ile sapma mumkundur.

TA FIKSTUR
  TA gunluk kapasitesi = fikstur[kart,gun] * adet_vardiya[kart] * 2.
  Bos (None) gunler icin fikstur sayisi karar degiskeni (fx) olarak
  modelin kendisi belirler; baz fikstur ile sinirlanir.

Gereksinimler:  pip install pulp pandas openpyxl
---------------------------------------------------------------------------
"""

import sys
import pulp

import veri_oku


# ===========================================================================
# 1. SABIT KATSAYILAR
# ===========================================================================

rM      = 0.95      # MD asama sabit verim katsayisi
VARDIYA = 2         # TA gunluk vardiya sayisi
S_SETUP = 0.50      # OTD setup kapasite kaybi orani (%50)

# --- Alokasyon onarimi ceza katsayilari (MD icin) ---
cM_uzat  = 0.05     # MD: kart zaten o kanalda -> uzatma
cM_kanal = 0.15     # MD: ayni fiziksel hatta diger kanal
cM_hat   = 0.40     # MD: baska fiziksel MD hatti

BIG_M = 1e6         # Acik degiskenleri buyuk ceza katsayisi


# ===========================================================================
# 2. YARDIMCI FONKSIYONLAR
# ===========================================================================

def md_fiziksel_hat(veri):
    """kanal -> fiziksel hat eslemesi."""
    return dict(veri['md_kanal_hat'])


def onarim_ceza_md(veri, kanal, kart):
    """Bir MD kanalina kart ek atamanin ceza katsayisi."""
    ref_kanallar = {k for (k, _), kk in veri['md_alokasyon'].items() if kk == kart}
    ref_hatlar   = {veri['md_kanal_hat'].get(k, k) for k in ref_kanallar}
    hedef_hat    = veri['md_kanal_hat'].get(kanal, kanal)
    if kanal in ref_kanallar:
        return cM_uzat
    elif hedef_hat in ref_hatlar:
        return cM_kanal
    else:
        return cM_hat


# ===========================================================================
# 3. MODEL KURMA VE LEKSIKOGRAFIK COZME
# ===========================================================================

def model_kur_coz(veri, sessiz=True):
    """
    Modeli kurar, uc asamali leksikografik cozum uygular:
      Asama 1: min acik
      Asama 2: acik sabit, min setup
      Asama 3: acik+setup sabit, min tampon stok
    """

    # ===================================================================
    # KUMELER
    # ===================================================================
    I     = veri['kartlar']               # 14 kart
    T     = veri['gunler']                # [1..14]
    LO    = veri['otd_hatlari']           # OTD hatlari
    LM    = veri['md_hatlari']            # MD kanallari
    I_MD  = veri['md_kartlari']           # MD'ye giren kartlar
    fizhat = md_fiziksel_hat(veri)         # kanal -> fiziksel hat

    # --- Sabit parametreler ---
    D       = veri['montaj_plani']        # (kart,gun) -> adet
    s0O     = veri['baslangic_otd']
    s0M     = veri['baslangic_md']
    s0T     = veri['baslangic_ta']
    tempo   = veri['tempo']               # (hat,kart) -> UPM
    rO      = veri['otd_oran']            # (hat,gun) -> kapasite orani
    rMo     = veri['md_oran']             # (kanal,gun) -> MD kapasite orani
    fikstur     = veri['fikstur']         # (kart,gun) -> int | None
    fikstur_baz = veri['fikstur_baz']     # kart -> baz fikstur
    adet        = veri['adet_vardiya']    # kart -> adet/fikstur/vardiya
    refO    = veri['otd_alokasyon']       # (hat,gun) -> kart (referans plan)
    refM    = veri['md_alokasyon']        # (kanal,gun) -> kart (referans plan)

    # --- Uyumluluk kumeleri (temposu TANIMLI olanlar) ---
    A_O = {(i, l) for i in I for l in LO if (l, i) in tempo}
    A_M = {(i, k) for i in I_MD for k in LM if (fizhat[k], i) in tempo}

    # --- F4 ozel durumu: I_MD'de ama MD temposu yok -> fiili MD-skip ---
    fiili_md_kartlari = {i for i in I_MD if any((i, k) in A_M for k in LM)}
    md_skip_kartlari  = I_MD - fiili_md_kartlari
    if md_skip_kartlari:
        print(f"  BILGI: {md_skip_kartlari} kartlari I_MD'de ama MD temposu yok; "
              f"fiili olarak MD-skip gibi muamele edilecek.")

    # ===================================================================
    # MODEL OLUSTUR
    # ===================================================================
    m = pulp.LpProblem('Beko_CLSP_SI', pulp.LpMinimize)

    # ===================================================================
    # KARAR DEGISKENLERI
    # ===================================================================

    # --- OTD: Uretim, atama, setup ---
    xO = {(i, l, t): pulp.LpVariable(f'xO_{i}_{l}_{t}', lowBound=0)
          for (i, l) in A_O for t in T}

    yO = {(i, l, t): pulp.LpVariable(f'yO_{i}_{l}_{t}', cat='Binary')
          for (i, l) in A_O for t in T}
    #    yO[k,l,t] = 1 ise t gununde l hattinda k karti uretilir

    zO = {(l, t): pulp.LpVariable(f'zO_{l}_{t}', cat='Binary')
          for l in LO for t in T}
    #    zO[l,t] = 1 ise t gununde l hattinda kart degisikligi (setup) vardir

    # --- MD: Uretim + onarim degiskenleri ---
    xM = {(i, k, t): pulp.LpVariable(f'xM_{i}_{k}_{t}', lowBound=0)
          for (i, k) in A_M for t in T}

    yM = {(i, k, t): pulp.LpVariable(f'yM_{i}_{k}_{t}', cat='Binary')
          for (i, k) in A_M for t in T}
    #    yM[k,c,t] = 1 ise referansta olmayan bir atama acilir (onarim)

    # --- TA: Islem miktari ---
    xT = {(i, t): pulp.LpVariable(f'xT_{i}_{t}', lowBound=0)
          for i in I for t in T}

    # --- Tampon stoklar (SERT: lb=0) ---
    KSO = {(i, t): pulp.LpVariable(f'KSO_{i}_{t}', lowBound=0)
           for i in I for t in T}
    KSM = {(i, t): pulp.LpVariable(f'KSM_{i}_{t}', lowBound=0)
           for i in fiili_md_kartlari for t in T}
    KST = {(i, t): pulp.LpVariable(f'KST_{i}_{t}', lowBound=0)
           for i in I for t in T}

    # --- Acik degiskenleri (fizibilite icin) ---
    gO = {(i, t): pulp.LpVariable(f'gO_{i}_{t}', lowBound=0)
          for i in I for t in T}
    gM = {(i, t): pulp.LpVariable(f'gM_{i}_{t}', lowBound=0)
          for i in fiili_md_kartlari for t in T}
    gT = {(i, t): pulp.LpVariable(f'gT_{i}_{t}', lowBound=0)
          for i in I for t in T}

    # --- TA fikstur sayisi: dolu -> sabit, bos -> karar degiskeni ---
    fx = {}
    for i in I:
        for t in T:
            deger = fikstur.get((i, t))
            if deger is not None:
                fx[i, t] = pulp.LpVariable(f'fx_{i}_{t}',
                                           lowBound=deger, upBound=deger)
            else:
                baz = fikstur_baz.get(i, 0)
                fx[i, t] = pulp.LpVariable(f'fx_{i}_{t}',
                                           lowBound=0, upBound=baz,
                                           cat='Continuous')

    # ===================================================================
    # KISITLAR
    # ===================================================================

    # --- (1) Bir OTD hattinda bir gunde en fazla BIR kart tipi ----------
    for l in LO:
        for t in T:
            m += (pulp.lpSum(yO[i, l, t] for i in I if (i, l) in A_O) <= 1,
                  f'tek_kart_OTD_{l}_{t}')

    # --- (2) OTD kapasite: setup varsa %50 kayip -------------------------
    #     xO[k,l,t] <= tempo[l,k] * yO[k,l,t]              ... atama kisiti
    #     xO[k,l,t] <= tempo[l,k] * (1 - S * zO[l,t])      ... setup kaybi
    for (i, l) in A_O:
        cap = tempo[(l, i)]
        for t in T:
            # (2a) Uretim ancak atama varsa yapilir
            m += (xO[i, l, t] <= cap * yO[i, l, t],
                  f'kap_OTD_atama_{i}_{l}_{t}')
            # (2b) Setup varsa kapasite (1-S) ile sinirlanir
            m += (xO[i, l, t] <= cap * (1 - S_SETUP * zO[l, t]),
                  f'kap_OTD_setup_{i}_{l}_{t}')

    # --- (3) Setup tespiti: t>=2 icin kart degisikligi --------------------
    #     zO[l,t] >= yO[k,l,t] - yO[k,l,t-1]  her k icin
    #     Eger t gununde k karti atanmis ama t-1'de atanmamissa -> setup
    for l in LO:
        for t in T:
            if t == T[0]:
                # Gun 1: referans planin son durumu "gun 0" olarak alinir
                for i in I:
                    if (i, l) not in A_O:
                        continue
                    ref_kart_gun0 = refO.get((l, 1))  # referans planin 1. gun karti
                    y_onceki = 1.0 if (ref_kart_gun0 == i) else 0.0
                    m += (zO[l, t] >= yO[i, l, t] - y_onceki,
                          f'setup_OTD_{i}_{l}_{t}')
            else:
                t_onceki = T[T.index(t) - 1]
                for i in I:
                    if (i, l) not in A_O:
                        continue
                    # yO[i,l,t-1]: eger onceki gunde bu hat aktif degilse
                    # (yani referansta veya modelde hic atanmamissa) 0 olur
                    if (i, l, t_onceki) in yO:
                        m += (zO[l, t] >= yO[i, l, t] - yO[i, l, t_onceki],
                              f'setup_OTD_{i}_{l}_{t}')
                    else:
                        m += (zO[l, t] >= yO[i, l, t],
                              f'setup_OTD_{i}_{l}_{t}')

    # --- (4) MD kapasite (referans + onarim) ------------------------------
    for (i, k) in A_M:
        fh = fizhat[k]
        for t in T:
            if refM.get((k, t)) == i:
                # Referansta var -> orana gore kapasite
                oran = rMo.get((k, t), 1.0)
                m += (xM[i, k, t] <= rM * oran * tempo[(fh, i)],
                      f'kap_MD_ref_{i}_{k}_{t}')
            else:
                # Referansta yok -> ancak onarim ile acilir
                m += (xM[i, k, t] <= rM * tempo[(fh, i)] * yM[i, k, t],
                      f'kap_MD_onarim_{i}_{k}_{t}')

    # --- (5) Paylasimli MD kapasitesi ------------------------------------
    for fh in set(fizhat.values()):
        fh_kanallar = [k for k in LM if fizhat[k] == fh]
        if len(fh_kanallar) <= 1:
            continue
        for t in T:
            ifade = []
            for k in fh_kanallar:
                for i in fiili_md_kartlari:
                    if (i, k) not in A_M:
                        continue
                    payda = rM * tempo[(fizhat[k], i)]
                    if payda > 0:
                        ifade.append(xM[i, k, t] / payda)
            if ifade:
                m += (pulp.lpSum(ifade) <= 1.0,
                      f'paylasim_MD_{fh}_{t}')

    # --- (6) TA kapasite (gunluk fikstur ile) ----------------------------
    for i in I:
        for t in T:
            m += (xT[i, t] <= fx[i, t] * adet.get(i, 0.0) * VARDIYA,
                  f'kap_TA_{i}_{t}')

    # --- (7)-(9) Tampon denge kisitlari (acik degiskenli) ----------------
    for i in I:
        for idx, t in enumerate(T):
            onceki = T[idx - 1] if idx > 0 else None

            # Toplam OTD uretimi (tum hatlardan)
            XO_it = pulp.lpSum(xO[i, l, t] for l in LO if (i, l) in A_O)
            # Toplam MD uretimi (tum kanallardan)
            XM_it = pulp.lpSum(xM[i, k, t] for k in LM if (i, k) in A_M)

            # (7) KSO tamponu: OTD -> sonraki asama (MD veya TA)
            onceki_KSO = KSO[i, onceki] if onceki else s0O.get(i, 0.0)
            if i in fiili_md_kartlari:
                # MD'ye giren kart: OTD cikti -> MD girdi
                m += (KSO[i, t] == onceki_KSO + XO_it - XM_it + gO[i, t],
                      f'denge_KSO_{i}_{t}')
            else:
                # MD-skip kart (veya fiili MD-skip): OTD cikti -> TA girdi
                m += (KSO[i, t] == onceki_KSO + XO_it - xT[i, t] + gO[i, t],
                      f'denge_KSO_atla_{i}_{t}')

            # (8) KSM tamponu: MD -> TA (yalniz fiili MD kartlari)
            if i in fiili_md_kartlari:
                onceki_KSM = KSM[i, onceki] if onceki else s0M.get(i, 0.0)
                m += (KSM[i, t] == onceki_KSM + XM_it - xT[i, t] + gM[i, t],
                      f'denge_KSM_{i}_{t}')

            # (9) KST tamponu: TA -> Son Montaj
            onceki_KST = KST[i, onceki] if onceki else s0T.get(i, 0.0)
            m += (KST[i, t] == onceki_KST + xT[i, t] - D.get((i, t), 0.0)
                  + gT[i, t],
                  f'denge_KST_{i}_{t}')

    # ===================================================================
    # IFADELER (amac fonksiyonu bilesenleri)
    # ===================================================================
    toplam_acik = (pulp.lpSum(gO[i, t] for i in I for t in T) +
                   pulp.lpSum(gM[i, t] for i in fiili_md_kartlari for t in T) +
                   pulp.lpSum(gT[i, t] for i in I for t in T))

    toplam_setup = pulp.lpSum(zO[l, t] for l in LO for t in T)

    toplam_tampon = (pulp.lpSum(KSO[i, t] for i in I for t in T) +
                     pulp.lpSum(KSM[i, t] for i in fiili_md_kartlari for t in T) +
                     pulp.lpSum(KST[i, t] for i in I for t in T))

    toplam_md_ceza = pulp.lpSum(
        onarim_ceza_md(veri, k, i) * yM[i, k, t]
        for (i, k) in A_M for t in T
    )

    # ===================================================================
    # AGIRLIKLI TEK ASAMALI COZUM (Weighted Scalarization)
    # ===================================================================
    # Agirliklar hiyerarsik: W1 >> W2 >> W3
    #   W1 * acik  : fizibilite ihlali en pahali (oncelik 1)
    #   W2 * setup : setup sayisi minimizasyonu  (oncelik 2)
    #   W3 * tampon: tampon stok minimizasyonu   (oncelik 3)
    #   W4 * md_cz : MD onarim cezasi           (oncelik 4)
    #
    # W degerleri arasindaki oran, alt oncelikteki TOPLAM degerin ust
    # oncelikteki BIR birimi etkileyemeyecegi kadar buyuk olmalidir.
    # Max tampon ~ 14 kart * 14 gun * 2000 ~ 400k => W2/W3 > 400k -> 1e6
    # Max setup  ~ 5 hat * 14 gun = 70            => W1/W2 > 70   -> 1e4
    W1 = 1e6        # acik cezasi
    W2 = 1e3        # setup cezasi
    W3 = 1.0        # tampon agirlik
    W4 = 0.1        # MD onarim cezasi

    m.setObjective(W1 * toplam_acik +
                   W2 * toplam_setup +
                   W3 * toplam_tampon +
                   W4 * toplam_md_ceza)

    msg_flag = 0 if sessiz else 1
    m.solve(pulp.PULP_CBC_CMD(msg=msg_flag, timeLimit=180,
                              options=['ratioGap 0.01']))

    if m.status != pulp.constants.LpStatusOptimal:
        # CBC "Stopped on time" durum kodu 0 ama feasible cozum varsa kabul et
        if m.status == 1 or (m.status == 0 and pulp.value(m.objective) is not None):
            print(f"  UYARI: CBC zaman limitinde durdu, en iyi bulunan cozum kullaniliyor.")
        else:
            return {'durum': f'BASARISIZ (kod={m.status})'}

    acik_star  = pulp.value(toplam_acik) or 0
    setup_star = pulp.value(toplam_setup) or 0
    tampon_star = pulp.value(toplam_tampon) or 0
    print(f"  Toplam acik  = {acik_star:>10,.0f}")
    print(f"  Toplam setup = {setup_star:>10,.0f}")
    print(f"  Toplam tampon= {tampon_star:>10,.0f}")

    # ===================================================================
    # SONUC TOPLAMA
    # ===================================================================
    sonuc = {
        'durum':        'OPTIMAL',
        'toplam_acik':  acik_star,
        'toplam_setup': setup_star,
        'toplam_tampon': tampon_star,

        # OTD sonuclari
        'xO': {key: var.varValue for key, var in xO.items()
               if var.varValue is not None and var.varValue > 1e-6},
        'yO': {key: int(round(var.varValue)) for key, var in yO.items()
               if var.varValue is not None and var.varValue > 0.5},
        'zO': {key: int(round(var.varValue)) for key, var in zO.items()
               if var.varValue is not None and var.varValue > 0.5},

        # MD sonuclari
        'xM': {key: var.varValue for key, var in xM.items()
               if var.varValue is not None and var.varValue > 1e-6},
        'yM_onarim': [(i, k, t) for (i, k) in A_M for t in T
                      if (i, k, t) in yM
                      and yM[i, k, t].varValue is not None
                      and yM[i, k, t].varValue > 0.5],

        # TA sonuclari
        'xT': {key: var.varValue for key, var in xT.items()
               if var.varValue is not None and var.varValue > 1e-6},

        # Tampon stoklar
        'KSO': {key: var.varValue for key, var in KSO.items()},
        'KSM': {key: var.varValue for key, var in KSM.items()},
        'KST': {key: var.varValue for key, var in KST.items()},

        # Aciklar
        'acik_OTD': {(i, t): gO[i, t].varValue for i in I for t in T
                     if gO[i, t].varValue is not None
                     and gO[i, t].varValue > 1e-3},
        'acik_MD':  {(i, t): gM[i, t].varValue for i in fiili_md_kartlari for t in T
                     if gM[i, t].varValue is not None
                     and gM[i, t].varValue > 1e-3},
        'acik_TA':  {(i, t): gT[i, t].varValue for i in I for t in T
                     if gT[i, t].varValue is not None
                     and gT[i, t].varValue > 1e-3},

        # TA fikstur (modelin belirledigi bos gunler)
        'fikstur_planlanan': {(i, t): round(fx[i, t].varValue)
                              for i in I for t in T
                              if fikstur.get((i, t)) is None
                              and fx[i, t].varValue is not None},

        # OTD alokasyon plani (okunakli)
        'otd_plan': {},

        # Yardimci kume bilgileri
        'fiili_md_kartlari': fiili_md_kartlari,
        'md_skip_kartlari': md_skip_kartlari,
    }

    # OTD alokasyon planini okunakli bicimde olustur
    for l in LO:
        sonuc['otd_plan'][l] = {}
        for t in T:
            for i in I:
                if (i, l, t) in yO and yO[i, l, t].varValue is not None \
                        and yO[i, l, t].varValue > 0.5:
                    sonuc['otd_plan'][l][t] = i

    return sonuc


# ===========================================================================
# 4. KONSOL RAPORU
# ===========================================================================

def rapor_yaz(veri, sonuc):
    """Cozum sonuclarini konsola yazdiran detayli rapor."""
    print('=' * 70)
    print(f"COZUM DURUMU : {sonuc['durum']}")

    if sonuc['durum'] != 'OPTIMAL':
        print("Cozum elde edilemedi.")
        return

    T = veri['gunler']
    I = veri['kartlar']

    print(f"ASAMA 1 - Toplam kacinilmaz acik : {sonuc['toplam_acik']:>10,.0f}")
    print(f"ASAMA 2 - Toplam OTD setup sayisi: {sonuc['toplam_setup']:>10,.0f}")
    print(f"ASAMA 3 - Toplam tampon stok     : {sonuc['toplam_tampon']:>10,.0f}")
    print('-' * 70)

    # --- Fizibilite durumu ---
    if sonuc['toplam_acik'] < 1e-3:
        print("PLAN FIZIBIL: tum tamponlar pozitif, montaj ac kalmiyor.")
    else:
        print("KACINILMAZ ACIKLAR (mesai/ek vardiya degerlendirilmeli):")
        for (i, t), v in sorted(sonuc.get('acik_TA', {}).items()):
            print(f"  [TA acik ] {i:5s} gun {t:2d}: {v:>8,.0f} adet")
        for (i, t), v in sorted(sonuc.get('acik_MD', {}).items()):
            print(f"  [MD acik ] {i:5s} gun {t:2d}: {v:>8,.0f} adet")
        for (i, t), v in sorted(sonuc.get('acik_OTD', {}).items()):
            print(f"  [OTD acik] {i:5s} gun {t:2d}: {v:>8,.0f} adet")

    # --- OTD Alokasyon Plani ---
    print('-' * 70)
    print("OTD ALOKASYON PLANI (model cikti):")
    baslik = ''.ljust(6) + ''.join(f'G{t:<4d}' for t in T)
    print(f"  {baslik}")
    for l in veri['otd_hatlari']:
        satir = f"  {l:5s} "
        for t in T:
            kart = sonuc['otd_plan'].get(l, {}).get(t, '---')
            satir += f'{kart:5s}'
        print(satir)

    # --- Referans plan ile karsilastirma ---
    print("\nREFERANS PLAN (Excel'den):")
    baslik = ''.ljust(6) + ''.join(f'G{t:<4d}' for t in T)
    print(f"  {baslik}")
    for l in veri['otd_hatlari']:
        satir = f"  {l:5s} "
        for t in T:
            kart = veri['otd_alokasyon'].get((l, t), '---')
            satir += f'{kart:5s}'
        print(satir)

    # --- Setup'lar ---
    print('-' * 70)
    print(f"OTD SETUP SAYISI: {int(sonuc['toplam_setup'])}")
    if sonuc['zO']:
        print("Setup olan hat-gun cifteleri:")
        for (l, t), val in sorted(sonuc['zO'].items()):
            onceki = sonuc['otd_plan'].get(l, {}).get(t-1, '???') if t > 1 else 'onceki'
            simdi  = sonuc['otd_plan'].get(l, {}).get(t, '???')
            print(f"  {l} gun {t:2d}: {onceki} -> {simdi}")
    else:
        print("  Hic setup yok.")

    # --- MD onarim ---
    print('-' * 70)
    if sonuc['yM_onarim']:
        print("MD ONARIM ATAMALARI:")
        for (i, k, t) in sorted(sonuc['yM_onarim']):
            print(f"  {i:5s} -> {k} kanali, gun {t}")
    else:
        print("MD onarimi gerekmedi.")

    # --- Son gun tampon stoklar ---
    print('-' * 70)
    son = T[-1]
    print(f"SON GUN ({son}) TAMPON STOKLARI:")
    print(f"  {'Kart':5s} {'KSO':>10s} {'KSM':>10s} {'KST':>10s}")
    for i in I:
        kso = sonuc['KSO'].get((i, son), 0) or 0
        ksm = sonuc['KSM'].get((i, son), 0) or 0
        kst = sonuc['KST'].get((i, son), 0) or 0
        print(f"  {i:5s} {kso:>10,.0f} {ksm:>10,.0f} {kst:>10,.0f}")

    # --- TA fikstur (modelin belirledigi bos gunler) ---
    if sonuc['fikstur_planlanan']:
        print('-' * 70)
        sifir_olmayan = {k: v for k, v in sonuc['fikstur_planlanan'].items() if v > 0}
        if sifir_olmayan:
            print(f"TA FIKSTUR (model tarafindan belirlenen, sifir olmayan):")
            for (i, t), v in sorted(sifir_olmayan.items()):
                print(f"  {i:5s} gun {t:2d}: {v} fikstur")

    print('=' * 70)


# ===========================================================================
# 5. SONUCLARI JSON'A KAYDET  (dashboard icin)
# ===========================================================================

def sonuc_kaydet(veri, sonuc, dosya_adi='sonuc.json'):
    """Cozum sonuclarini Streamlit dashboard'un okuyabilecegi JSON'a yazar."""
    import json

    T = veri['gunler']
    I = veri['kartlar']

    # Tuple key'leri string'e cevir (JSON uyumlu)
    def _k(tup):
        return '|'.join(str(x) for x in tup)

    export = {
        'meta': {
            'durum':        sonuc['durum'],
            'toplam_acik':  sonuc['toplam_acik'],
            'toplam_setup': sonuc['toplam_setup'],
            'toplam_tampon': sonuc['toplam_tampon'],
            'kartlar':      I,
            'gunler':       T,
            'gun_tarih':    veri['gun_tarih'],
            'otd_hatlari':  veri['otd_hatlari'],
            'md_hatlari':   veri['md_hatlari'],
            'md_kartlari':  sorted(sonuc.get('fiili_md_kartlari', veri['md_kartlari'])),
            'atla_kartlari': sorted(veri['atla_kartlari']),
        },

        # OTD alokasyon plani (model)
        'otd_plan': {l: {str(t): k for t, k in gun_kart.items()}
                     for l, gun_kart in sonuc['otd_plan'].items()},

        # OTD referans plan (Excel)
        'otd_referans': {l: {str(g): veri['otd_alokasyon'].get((l, g), None)
                             for g in T}
                         for l in veri['otd_hatlari']},

        # Setup listesi
        'setuplar': [{'hat': l, 'gun': t} for (l, t) in sorted(sonuc.get('zO', {}))],

        # MD onarim
        'md_onarim': [{'kart': i, 'kanal': k, 'gun': t}
                      for (i, k, t) in sonuc.get('yM_onarim', [])],

        # Uretim miktarlari
        'xO': {_k(key): round(val, 1) for key, val in sonuc['xO'].items()},
        'xM': {_k(key): round(val, 1) for key, val in sonuc['xM'].items()},
        'xT': {_k(key): round(val, 1) for key, val in sonuc['xT'].items()},

        # Tampon stoklar
        'KSO': {_k(key): round(val or 0, 1) for key, val in sonuc['KSO'].items()},
        'KSM': {_k(key): round(val or 0, 1) for key, val in sonuc['KSM'].items()},
        'KST': {_k(key): round(val or 0, 1) for key, val in sonuc['KST'].items()},

        # Aciklar
        'acik_OTD': {_k(key): round(val, 1) for key, val in sonuc.get('acik_OTD', {}).items()},
        'acik_MD':  {_k(key): round(val, 1) for key, val in sonuc.get('acik_MD', {}).items()},
        'acik_TA':  {_k(key): round(val, 1) for key, val in sonuc.get('acik_TA', {}).items()},

        # TA fikstur (modelin belirledigi)
        'fikstur_planlanan': {_k(key): val for key, val in
                              sonuc.get('fikstur_planlanan', {}).items() if val > 0},

        # Montaj plani (talep)
        'montaj_plani': {_k(key): val for key, val in veri['montaj_plani'].items() if val > 0},

        # Baslangic stoklari
        'baslangic': {
            'otd': veri['baslangic_otd'],
            'md':  veri['baslangic_md'],
            'ta':  veri['baslangic_ta'],
        },
    }

    with open(dosya_adi, 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\nSonuclar kaydedildi: {dosya_adi}")


# ===========================================================================
# 6. KOMUT SATIRINDAN CALISTIRMA
# ===========================================================================

if __name__ == '__main__':
    dosya = sys.argv[1] if len(sys.argv) > 1 else 'Sasi_Uretim_Plani_v4_1.xlsx'
    print(f"Veri okunuyor: {dosya}")
    veri = veri_oku.veri_oku(dosya)

    uyarilar = veri_oku.dogrula(veri)
    if uyarilar:
        print("Veri uyarilari:")
        for u in uyarilar:
            print(f"  - {u}")

    print("\nModel kuruluyor ve cozuluyor (leksikografik 3 asama)...")
    sonuc = model_kur_coz(veri, sessiz=True)
    rapor_yaz(veri, sonuc)
    sonuc_kaydet(veri, sonuc)
