# FlightWall shopping list

This list supports the [beginner wiring guide](beginner-wiring-guide.md): twenty 16×16 **5 V WS2812B** panels, one classic ESP32, and **five independent four-panel power groups**. Use the [build plan](flightwall-build-plan.md) to buy and test in stages. Full-wall quantities are **totals**, not additions to the practice quantity.

Links are purchasing examples, mostly for the US. Retailer pages could not be fetched from this workspace's restricted network on October 3, 2026; **stock, price, current listing contents, certifications, and connector ratings have not been verified**. Product/category searches are labeled as such. Match the specifications below and the maker's datasheet before ordering; a listing title or photo is insufficient. No affiliate links are used.

## First order: tools and one panel

Buy one panel, one ESP32, one 5 V / 4 A supply, one DC adapter, one fuse block, one main fuse holder, the buffer components, wire, and the essential tools. Test those exact parts together before ordering nineteen more panels and four more supplies. Buy all twenty panels from the same specification/batch where possible; one spare is useful.

## Electronics and power

| Item | One-panel practice | Full-wall total | Required specification / purchase example |
| --- | --- | --- | --- |
| LED matrix panel | 1 | **20**, optional 1 spare | **16×16, 256 RGB LEDs, 5 V WS2812B-compatible**, DIN/DOUT, accessible +5 V/GND power connections. Confirm pixel order, pigtails, mounting, and dimensions. [Original project's AliExpress listing](https://www.aliexpress.us/item/2255800358269772.html); [Adafruit 16×16 flexible NeoPixel matrix example](https://www.adafruit.com/product/2547). A different panel may need mapping changes. |
| ESP32 development board | 1 | **1** | Classic **ESP32-WROOM-32**, USB interface, accessible GPIO25 and GND. [Original HiLetgo R32 D1 example](https://www.amazon.com/HiLetgo-ESP-32-Development-Bluetooth-Arduino/dp/B07WFZCBH8); [ESP32-WROOM-32 dev-board search](https://www.amazon.com/s?k=ESP32+WROOM+32+development+board+GPIO25). Avoid substituting C3/S3 without adapting the pin/firmware configuration. |
| LED power supply | 1 | **5** | Factory-enclosed, isolated, regulated **5 V DC / 4 A continuous**, center-positive output, documented regional safety approvals, compatible mains cord/plug. [Adafruit 5 V / 4 A supply example](https://www.adafruit.com/product/1466); [Mean Well GST25A05-P1J distributor search](https://www.digikey.com/en/products?keywords=GST25A05-P1J). Verify the chosen part's datasheet and order the matching AC cord if sold separately. This procedure does not use exposed L/N/earth terminals. |
| Matching DC output adapter/pigtail | 1 | **5** | Female **5.5×2.1 mm** barrel jack for the example supplies, documented **≥5 A** rating, polarity identified; 18 AWG or suitably rated leads/terminals. [Rated 5 A DC-jack purchasing search](https://www.amazon.com/s?k=5.5+2.1+female+DC+power+jack+5A+18AWG). Many cheap adapters have no reliable current rating; choose a documented part or change to a complete rated harness. |
| Inline main fuse holder | 1 | **5** | Covered holder accepting the chosen **3 A** DC fuse, documented ≥5 A capability, suitable stranded-copper leads. Fit close to each DC jack. [ATO/ATC inline-holder search](https://www.amazon.com/s?k=ATO+ATC+inline+fuse+holder+copper+wire). Match fuse format to holder; do not buy a 30 A fuse just because one is included. |
| Covered distribution fuse block | 1 | **5** | At least **4 individually fused positive outputs**, separate negative bus or matching negative terminal block, documented input ≥5 A, terminals suitable for 18 AWG, accepts **1 A** branch fuses. A six-way block leaves two unused outputs. [Six-way block with negative-bus search](https://www.amazon.com/s?k=6+way+blade+fuse+block+negative+bus+cover). Optional indicator lamps may not work at 5 V. |
| Main fuses | 1 + spare | **5 × 3 A**, plus ≥5 spares | DC rated for at least the operating voltage, matching the inline holders. [3 A ATO/ATC fuse search](https://www.amazon.com/s?k=3+amp+ATO+ATC+blade+fuses). |
| Panel fuses | 1 + spare | **20 × 1 A**, plus ≥5 spares | Same physical format as the distribution block, appropriate DC rating. [1 A ATO/ATC fuse search](https://www.amazon.com/s?k=1+amp+ATO+ATC+blade+fuses). **1 A is not 10 A**; common assorted kits may omit 1 A. |
| Data buffer IC | 1 | **1**, optional spare | **SN74AHCT125N / 74AHCT125, 14-pin DIP**. [Adafruit 74AHCT125 example](https://www.adafruit.com/product/1787); [Digi-Key part-number search](https://www.digikey.com/en/products?keywords=SN74AHCT125N). Buy the DIP package for the guide's pin table. Generic BSS138 I²C shifters and 74HC125 are not equivalent choices here. |
| IC socket | 1 | **1** | 14-pin DIP socket matching chip width. [14-pin DIP-socket search](https://www.amazon.com/s?k=14+pin+DIP+IC+socket). Recommended for a soldered board. |
| Small perfboard and signal terminal/header kit | 1 set | **1 set** | Enough room for socket, capacitors, resistors, short wiring, and insulated mounting. [Perfboard/terminal kit search](https://www.amazon.com/s?k=perfboard+prototype+board+screw+terminal+kit). A temporary solderless breadboard is only for the low-current buffer circuit. |
| Data resistor | 1 | **1**, buy small pack | **330 Ω, ¼ W**. [330-ohm resistor search](https://www.amazon.com/s?k=330+ohm+resistor+1%2F4+watt). |
| Buffer input pull-down resistor | 1 | **1**, buy small pack | **10 kΩ, ¼ W**. [10-kilohm resistor search](https://www.amazon.com/s?k=10k+ohm+resistor+1%2F4+watt). |
| Buffer decoupling capacitor | 1 | **1**, buy small pack | **0.1 µF / 100 nF ceramic**, ≥10 V rating. [100-nF ceramic-capacitor search](https://www.amazon.com/s?k=100nF+0.1uF+ceramic+capacitor). |
| Group bulk capacitors | 1 | **5** | **1000 µF electrolytic**, ≥10 V (16 V is also suitable). Observe polarity. [1000-µF / 16-V capacitor search](https://www.amazon.com/s?k=1000uF+16V+electrolytic+capacitor). One per group's fused input. |
| ESP32 USB data cable | 1 | **1** | A **data-capable** cable matching the actual board's USB connector and computer. [Micro-USB data-cable search](https://www.amazon.com/s?k=micro+USB+data+cable); [USB-C data-cable search](https://www.amazon.com/s?k=USB+C+data+cable). Buy only the correct type; charge-only cables cannot upload firmware. |
| ESP32 USB charger | Computer USB for practice | **1**, if not already owned | Factory-enclosed, approved **5 V / ≥1 A USB supply**; a normal 5 V / 2 A charger is suitable. Match USB cable/port. [5 V USB-charger search](https://www.amazon.com/s?k=5V+2A+USB+charger+UL+listed). The LED supplies' positive outputs do not connect to this USB rail. |
| Power strip | Existing suitable strip | **1** | Approved for your country, with enough clearance/outlets for **five LED supplies + one ESP32 charger**; eight outlets leave room for a Pi or other existing equipment. Master switch, documented load rating. [Eight-outlet switched-strip search](https://www.amazon.com/s?k=8+outlet+power+strip+UL+listed+switch). Check adapter spacing before purchase. |

**Do not combine the five supplies' positive outputs.** Share their DC grounds and pass only data/ground between panels. The wiring guide explains the exact separation. Five 4 A supplies are five independent limits; they are not one unrestricted 20 A source.

## Wire, connectors, and insulation

Quantities assume short local feeds on a wall about 160 cm wide. Measure routes and buy a little extra before cutting. Use stranded **copper**, not copper-clad aluminum (CCA).

| Item | One-panel practice | Full-wall total | Specification / purchase link |
| --- | --- | --- | --- |
| Positive power wire | ~2 m | **~15 m / 50 ft red** | **18 AWG stranded copper**. Includes branch and short supply leads. [18-AWG red copper-wire search](https://www.amazon.com/s?k=18+AWG+stranded+copper+wire+red+50+feet). |
| Ground power wire | ~2 m | **~15 m / 50 ft black** | Same **18 AWG stranded copper**; allow for ground links among groups. [18-AWG black copper-wire search](https://www.amazon.com/s?k=18+AWG+stranded+copper+wire+black+50+feet). |
| Data/ground wire | ~1 m | **~7.5 m / 25 ft of paired cable** | About **22 AWG stranded copper**, two conductors run together; keep adjacent-panel links short. [22-AWG paired-wire search](https://www.amazon.com/s?k=22+AWG+2+conductor+stranded+copper+wire+25+feet). This is for signal links, not panel-power feeds. |
| Panel power connectors/pigtails | 1 pair if needed | **20 pairs if not supplied** | Match the panel's actual power connector, with documented rating suitable for the **1 A protected branch**; prefer ≥2 A. [Two-pin LED-power pigtail search](https://www.amazon.com/s?k=2+pin+LED+power+connector+pigtail+copper). Do not assume a random JST-style connector matches pin order, housing, or wire rating. Alternatively solder feeds to marked power pads. |
| Inter-panel data connectors/pigtails | None for a direct first-panel lead | **19 links**, plus buffer-to-P1 connection | Reuse suitable panel cables or buy matching mating pairs. [Three-pin WS2812B pigtail search](https://www.amazon.com/s?k=3+pin+WS2812B+connector+pigtail). **Remove/insulate the positive conductor**, leaving data and ground, and verify each modified cable. Buy a few extra pairs for mistakes. |
| Low-current jumper leads | Small set | **1 small set** | Correct gender for ESP32/prototype headers. [Dupont-jumper search](https://www.amazon.com/s?k=Dupont+jumper+wires+kit). GPIO/buffer signals only; not LED power. |
| Crimp terminals/ferrules | Small kit | **1 kit, ~100 usable terminations** | Match 18 AWG, stud diameters, and terminal type. Ring terminals for stud blocks; ferrules only where accepted by the screw-terminal maker. [18-AWG ring-terminal kit search](https://www.amazon.com/s?k=18+AWG+ring+terminal+kit); [ferrule kit search](https://www.amazon.com/s?k=18+AWG+wire+ferrule+kit+crimper). Inspect what sizes are actually included. |
| Heat-shrink tubing | Small assortment | **1 assortment** | Sizes for individual joints, cut positive ends, and pigtails. [Heat-shrink assortment search](https://www.amazon.com/s?k=heat+shrink+tubing+assortment). Electrical tape is supplemental, not a permanent splice. |
| Wire labels | Small sheet | **~100 labels** | Panel numbers, both ends of power feeds, groups, fuse values, and supply voltage. [Cable-label search](https://www.amazon.com/s?k=wrap+around+cable+labels). A permanent marker is also needed. |
| Cable restraints | Small pack | **~40 mounting clips + 100 ties** | Clips/strain relief suitable for backer; ties should not crush cable or flexible panels. [Cable-clip search](https://www.amazon.com/s?k=screw+mount+cable+clips); [cable-tie search](https://www.amazon.com/s?k=nylon+cable+ties). |

## Tools you need, including the volt meter

Reuse tools if they meet the specifications. Every tool below is one item/set unless otherwise stated.

| Tool | When needed | What to buy / purchase example |
| --- | --- | --- |
| **Digital multimeter with test leads** | **Required before first power-up** | DC volts covering 5 V, continuity/resistance, clear COM and V sockets. Auto-ranging is easiest. A Klein MM400-class meter or Fluke 101-class meter is suitable for these functions. [Klein auto-ranging meter search](https://www.amazon.com/s?k=Klein+MM400+multimeter); [Fluke 101 search](https://www.amazon.com/s?k=Fluke+101+multimeter). You do not need to use its amps function. |
| Insulated clip leads/probe clips | Required for repeatable voltage checks | Clips that fit the meter probes, insulated except at the contact, for attaching **with power off**. [Insulated meter-clip search](https://www.amazon.com/s?k=insulated+alligator+clips+multimeter+probes). Measurement leads do not become panel-power wiring. |
| Wire stripper | Required | Must handle **18 and 22 AWG stranded** wire without cutting strands. [Klein 11055 stripper search](https://www.amazon.com/s?k=Klein+11055+wire+stripper). |
| Flush/side cutters | Required | For wire, ties, and component leads. [Electronics flush-cutter search](https://www.amazon.com/s?k=electronics+flush+cutters). |
| Small flat and Phillips screwdrivers | Required | Fit the jack/fuse-block terminal screws; insulated handles. [Precision screwdriver-set search](https://www.amazon.com/s?k=precision+flat+phillips+screwdriver+set). Use the terminal maker's tightening guidance. |
| Insulated-terminal ratcheting crimper | If using ring/spade terminals | Correct die for the purchased terminals and **18 AWG** wire; pliers do not produce a controlled crimp. [Insulated-terminal crimper search](https://www.amazon.com/s?k=ratcheting+crimper+insulated+terminals+18+AWG). |
| Ferrule crimper | If the chosen terminals accept/need ferrules | Die covers your ferrule sizes; a ring-terminal crimper is not a substitute. [Ferrule-crimper kit search](https://www.amazon.com/s?k=wire+ferrule+crimping+tool+kit). |
| Small open-barrel connector crimper | Only if assembling loose connector pins | Match the exact pin family and wire size. [Engineer PA-09 example search](https://www.amazon.com/s?k=Engineer+PA-09+crimping+tool). Buying complete rated pigtails avoids this tool. |
| Temperature-controlled soldering station with stand | For DIP perfboard / bare panel pads | Station with local approved plug, suitable tip, stand, and cleaning sponge/brass wool. [Hakko FX-888DX station search](https://www.amazon.com/s?k=Hakko+FX-888DX+soldering+station). A complete station avoids buying a separate USB-PD supply/cable for a portable iron. |
| Electronics solder and flux | Whenever soldering | Small spool of fine electronics solder, about 0.6–0.8 mm, and compatible electronics flux. [Lead-free electronics solder search](https://www.amazon.com/s?k=lead+free+electronics+solder+0.6mm); [electronics flux-pen search](https://www.amazon.com/s?k=electronics+flux+pen). Do not buy plumbing solder/acid flux. |
| Fume extraction / ventilated soldering setup | Whenever soldering | Capture fumes away from your face; follow the solder/flux maker's instructions. [Solder-fume extractor search](https://www.amazon.com/s?k=solder+fume+extractor). |
| Helping-hands holder | Helpful for soldering | Holds wire/board while leaving both hands free. [PCB/third-hand holder search](https://www.amazon.com/s?k=PCB+helping+hands+soldering+holder). |
| Small heat gun | When fitting heat-shrink | Controlled heat; use away from panels/plastic, not a flame. [Electronics heat-gun search](https://www.amazon.com/s?k=mini+heat+gun+heat+shrink). |
| Safety glasses | Required for cutting/drilling/soldering | Proper eye protection. [Safety-glasses search](https://www.amazon.com/s?k=ANSI+Z87+safety+glasses). |
| Tape measure, level, and marker | For layout/mounting | [Tape-measure search](https://www.amazon.com/s?k=tape+measure); [level search](https://www.amazon.com/s?k=spirit+level); [permanent-marker search](https://www.amazon.com/s?k=permanent+marker). |
| Drill, matching bits, stud finder | If wall/backer mounting requires them | Choose for the wall/backer and fasteners; borrow if suitable. [Drill/bit search](https://www.amazon.com/s?k=cordless+drill+bit+set); [stud-finder search](https://www.amazon.com/s?k=stud+finder). |
| **DC-capable clamp meter** | Optional, for per-group current checks | Must explicitly measure **DC amps**, with useful resolution near 1–3 A; zero before measuring one conductor. [Klein CL390 example search](https://www.amazon.com/s?k=Klein+CL390+DC+clamp+meter). AC-only clamps and USB-only power meters are unsuitable for the LED-supply output. |

## Structure, mounting, and covers

| Item | Full-wall quantity | Specification / purchase link |
| --- | --- | --- |
| Rigid backer **or** printed-bracket assembly | 1 assembly | Size after measuring the panels. Allow room for distribution blocks, spacers, and ventilation. [Plywood/MDF purchasing search](https://www.homedepot.com/s/plywood%20project%20panel); print the repository's [rectangle bracket](../brackets/rectangle_bracket.stl) and [plus bracket](../brackets/plus_bracket.stl) if using the original style. The illustration suggests **20 rectangle + 9 plus brackets**; verify fit and required quantity before printing. Cardboard is not the finished structural backer. |
| Horizontal supports | **2**, cut to actual width | Original layout used two approximately **63-inch / 160-cm** wooden supports cut from 6-foot stock. Choose rigid stock and include it in the hanging weight. [Wood-trim purchasing search](https://www.homedepot.com/s/wood%20trim%206%20ft). |
| Screws / nylon spacers / mounting hardware | 1 matched set | Panel brackets, fuse blocks, buffer board, and supply mounts have different hole sizes. Fit your actual parts; use insulated clearance so boards/pads cannot touch screw tips or metal backer. [Nylon-spacer kit search](https://www.amazon.com/s?k=nylon+standoff+spacer+kit); [small-screw assortment search](https://www.amazon.com/s?k=small+wood+screw+assortment). |
| Buffer enclosure and terminal covers | **1 buffer enclosure**, covers for all five blocks | Insulating enclosure with strain relief; keep exposed positive terminals inaccessible. [Small ABS enclosure search](https://www.amazon.com/s?k=small+ABS+project+enclosure). Fuse-block covers may be included; check first. Do not enclose supplies without their required ventilation. |
| Wall hanging system / anchors | 1 system | Documented rating above the **measured complete wall weight**, compatible with wall material and suitable structure. [French-cleat purchasing search](https://www.homedepot.com/s/french%20cleat); [wall-anchor search](https://www.homedepot.com/s/wall%20anchors). A generic anchor kit is not proof of suitability. |

## Items already present or unnecessary for the wiring test

- A computer with a USB port runs [VS Code](https://code.visualstudio.com/) and [PlatformIO](https://platformio.org/install/ide?install=vscode), both free for this workflow. USB-port adapters may be needed for your computer.
- The existing local plan says a Raspberry Pi, readsb, SDR/ADS-B receiver, antenna, and Pi power supply already exist. **Reuse them.** See [the local implementation plan](flightwall-local-plan.md) rather than buying a duplicate receiver.
- Wi-Fi/LAN access is needed for flight information, but **not** for the bench LED test after the build tools are installed. Wokwi is optional and cannot validate real wiring or supply capacity.
- A solderless breadboard is optional for the signal prototype. A 3D printer is optional if you use a rigid backer or have brackets printed elsewhere. No oscilloscope is necessary for the prescribed initial checks.
- Paid flight-data accounts are unnecessary for the current local-Pi firmware. It polls the existing Pi's `/v1/flights` feed; cloud adapters remain legacy source files excluded from the production build. See [local firmware setup](../firmware/README.md#local-flight-data).

## Budget and ordering checks

These are **planning allowances, not quotes**: twenty panels approximately $300–700; five approved supplies $100–180; fused distribution, connectors, wire, buffer, and insulation $150–300; structure/hanging hardware $50–150; basic tools $80–180 if none are owned. Soldering equipment or a DC clamp can add roughly $80–200. Panel brand, shipping, and reuse of tools strongly affect the total; a premium-panel build can exceed these ranges.

Before checkout, check voltage, panel protocol, board GPIO25 access, supplied pigtails, connector current rating and pin order, fuse sizes/format, stranded-copper wire, local mains cord, and mounting fit. Start with the small order; do not substitute parts based only on an Amazon/AliExpress recommendation title.
