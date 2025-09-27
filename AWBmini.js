// À mettre dans le common.js du robot
// <nowiki>
mw.loader.using(['mediawiki.api', 'oojs-ui'], function () {
    const allowedUsers = ['JanusFr', 'BotJanus'];
    const currentUser = mw.config.get('wgUserName');

    if (!allowedUsers.includes(currentUser)) {
        console.warn('AWB.js : accès refusé - utilisateur non autorisé');
        return;
    }

    const api = new mw.Api();
    let pages = [];
    let index = 0;
    let portailAAjouter = '';
    let stopped = false; // Pour le bouton d'arrêt

    // Modules modifiables
    const modules = {
       stubAuto: {
        label: "Ajouter ou retirer {{stub}} selon la longueur",
        enabled: false,
        run: function (content) {
            if (mw.config.get('wgNamespaceNumber') !== 0) return content;

            const lengthWithoutStub = content.replace(/{{\s*stub\s*}}/gi, '').trim().length;
            const hasStub = /{{\s*stub\s*}}/i.test(content);
            const hasPortal = /{{\s*(portal|Portal)\s*\|[^}]+}}/i.test(content);

            // Retirer le modèle stub si l'article est devenu long
            if (lengthWithoutStub > 2000 && hasStub) {
                content = content.replace(/^\s*{{\s*stub\s*}}\s*\n?/im, '');
            }

            // Ajouter le modèle stub si l'article est court et n'en contient pas déjà un
            if (lengthWithoutStub < 1200 && !hasStub && hasPortal) {
                content = content.replace(/(^|\n)(\s*)({{\s*(portal|Portal)\s*\|[^}]+}})/i,
                    '\n{{stub}}\n$2$3');
            }

            return content;
        }
    },
        harmoniserTitres: {
            label: "Harmoniser les titres (espaces + majuscule)",
            enabled: false,
            run: function (content) {
                return content.replace(/^(\={2,6})\s*(.*?)\s*(\={2,6})\s*$/gm, (match, open, title, close) => {
                    title = title.trim();
                    if (!title) return '';
                    title = title.charAt(0).toUpperCase() + title.slice(1);
                    return `${open} ${title} ${close}`;
                });
            }
        },
        ajoutPortailParCategorie: {
            label: "Ajouter un portail selon la catégorie",
            enabled: false,
            run: function (content) {
                if (!portailAAjouter) return content;
                const portalRegex = /\{\{\s*[Pp]ortals?\s*\|([^}]+)\}\}/i;
                const lines = content.split('\n');
                let portalLineIndex = -1;
                let portails = [];
                for (let i = 0; i < lines.length; i++) {
                    const match = lines[i].match(portalRegex);
                    if (match) {
                        portalLineIndex = i;
                        portails = match[1].split('|').map(p => p.trim());
                        break;
                    }
                }
                if (!portails.map(p => p.toLowerCase()).includes(portailAAjouter.toLowerCase())) {
                    portails.push(portailAAjouter);
                }
                portails = portails.filter((p, i, arr) =>
                    arr.findIndex(x => x.toLowerCase() === p.toLowerCase()) === i
                );
                const newPortalLine = `{{portal|${portails.join('|')}}}`;
                if (portalLineIndex !== -1) {
                    lines.splice(portalLineIndex, 1);
                }
                let insertIndex = lines.length;
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    if (/^\[\[(Catégorie|Category):/i.test(line) ||
                        /^\[\[[a-z]{2,3}:/i.test(line) ||
                        /^\[\[(WP|wikipedia):/i.test(line)) {
                        insertIndex = i;
                        break;
                    }
                }
                lines.splice(insertIndex, 0, newPortalLine);
                return lines.join('\n');
            }
        },
        bienvenueNouveaux: {
            label: "Bienvenuter les nouveaux",
            enabled: false,
            run: async function (content, username) {
                if (!username) return null;
                const api = new mw.Api();
                const userTalkTitle = 'User talk:' + username;
                let pddData;
                try {
                    pddData = await api.get({
                        action: 'query',
                        titles: userTalkTitle,
                        prop: 'revisions',
                        rvprop: 'content',
                        formatversion: 2
                    });
                } catch (e) {
                    return `❌ Erreur API pour ${userTalkTitle}`;
                }
                const page = pddData.query.pages[0];
                if (!page.missing) {
                    return `⚠️ PDD déjà existante pour ${username}, ignoré.`;
                }
                let contribs;
                try {
                    contribs = await api.get({
                        action: 'query',
                        list: 'usercontribs',
                        ucuser: username,
                        uclimit: 1,
                        formatversion: 2
                    });
                } catch (e) {
                    return `❌ Erreur API (usercontribs) pour ${username}`;
                }
                if (!contribs.query.usercontribs || contribs.query.usercontribs.length === 0) {
                    return `❌ Aucun edit sur en.vikidia.org pour ${username}`;
                }
                try {
                    await api.postWithEditToken({
                        action: 'edit',
                        title: userTalkTitle,
                        text: '{{welcome}}~~~~',
                        summary: 'Bienvenue sur Vikidia !',
                        createonly: true
                    });
                    return `✅ Bienvenue laissé à ${username}`;
                } catch (e) {
                    return `❌ Erreur lors de la pose du message à ${username}`;
                }
            }
        },
        gérerOrphelin: {
            label: "Gérer {{orphan}}",
            enabled: false,
            run: async function (content, pageName) {
                const backlinksData = await api.get({
                    action: "query",
                    list: "backlinks",
                    bltitle: pageName,
                    bllimit: 1,
                    format: "json"
                });
                const isLinked = backlinksData?.query?.backlinks?.length > 0;
                const hasOrphan = /\{\{\s*[Oo]rphan\s*(\|[^}]*)?\s*\}\}/.test(content);

                if (isLinked && hasOrphan) {
                    return content.replace(/\{\{\s*[Oo]rphan\s*(\|[^}]*)?\s*\}\}\n?/i, '');
                }

                if (!isLinked && !hasOrphan) {
                    return `{{orphan}}\n${content}`;
                }

                return content;
            }
        }
    };

    async function getPagesFromCategory(fullCategoryName) {
        const res = await api.get({
            action: 'query',
            list: 'categorymembers',
            cmtitle: fullCategoryName,
            cmlimit: 'max',
            cmnamespace: 0,
            formatversion: 2
        });
        return res.query.categorymembers.map(p => p.title);
    }

    async function getRandomArticles(limit = 10) {
        const res = await api.get({
            action: 'query',
            list: 'random',
            rnnamespace: 0,
            rnlimit: limit,
            formatversion: 2
        });
        return res.query.random.map(p => p.title);
    }

    // Fonction utilitaire pour récupérer les utilisateurs actifs récents
    async function getRecentActiveUsers(limit = 10) {
        const api = new mw.Api();
        const res = await api.get({
            action: 'query',
            list: 'recentchanges',
            rcprop: 'user',
            rclimit: limit * 3, // on filtre après
            formatversion: 2
        });
        // On filtre pour ne garder que des noms uniques (non IP, non robots)
        const users = [];
        const seen = new Set();
        for (const rc of res.query.recentchanges) {
            if (!seen.has(rc.user)) {
                users.push(rc.user);
                seen.add(rc.user);
            }
            if (users.length >= limit) break;
        }
        return users;
    }

    function createUI() {
        const $box = $('<div>').css({
            position: 'fixed',
            top: '80px',
            right: '20px',
            width: '360px',
            background: '#fff',
            border: '1px solid #aaa',
            padding: '10px',
            zIndex: 10000,
            boxShadow: '2px 2px 5px rgba(0,0,0,0.2)',
            fontFamily: 'Arial, sans-serif'
        });
        $box.append('<h3 style="margin-top:0">AWB Vikidia</h3>');

        const $randomCheck = $('<input type="checkbox" id="awb-random">');
        const $randomLabel = $('<label for="awb-random"> Prendre 10 articles au hasard</label>');
        const $list = $('<textarea placeholder="Une page par ligne OU une liste de noms d\'utilisateur pour bienvenue...">').css({ width: '100%', height: '80px', marginBottom: '6px' });

        $randomCheck.on('change', async function () {
            if ($(this).prop('checked')) {
                $list.prop('disabled', true).val('Chargement des articles aléatoires...');
                pages = await getRandomArticles(10);
                $list.val(pages.join('\n'));
            } else {
                pages = [];
                $list.prop('disabled', false).val('');
            }
        });

        // Bouton pour récupérer des utilisateurs récents
        const $recentBtn = $('<button>Récupérer utilisateurs récents</button>').css({ margin: '4px 0', width: '100%' });
        $recentBtn.on('click', async function () {
            $recentBtn.prop('disabled', true).text('Chargement...');
            const users = await getRecentActiveUsers(10);
            $list.val(users.join('\n'));
            $recentBtn.prop('disabled', false).text('Récupérer utilisateurs récents');
        });

        const $modulesDiv = $('<div>').css({
            border: '1px solid #ccc',
            padding: '5px',
            margin: '10px 0',
            maxHeight: '120px',
            overflowY: 'auto',
            fontSize: '13px'
        }).append('<b>Modules à appliquer :</b><br>');

        Object.entries(modules).forEach(([key, mod]) => {
            const $checkbox = $('<input type="checkbox">').attr('id', `mod-${key}`).prop('checked', mod.enabled);
            const $label = $('<label>').attr('for', `mod-${key}`).text(' ' + mod.label);
            const $line = $('<div>').append($checkbox).append($label);
            $modulesDiv.append($line);
            $checkbox.on('change', () => { mod.enabled = $checkbox.prop('checked'); });
        });

        const $find = $('<input type="text" placeholder="Rechercher">').css({ width: '100%', marginTop: '4px' });
        const $replace = $('<input type="text" placeholder="Remplacer par">').css({ width: '100%', marginTop: '4px' });
        const $categoryInput = $('<input type="text" placeholder="Nom complet de la catégorie (ex: Category:History)">').css({ width: '100%', marginTop: '6px' });
        const $portailInput = $('<input type="text" placeholder="Portail à ajouter (ex: History)">').css({ width: '100%', marginTop: '4px' });
        const $summary = $('<input type="text" placeholder="Résumé d’édition">').css({ width: '100%', margin: '5px 0' });

        const $output = $('<div>').css({
            margin: '5px 0',
            color: '#007',
            height: '140px',
            overflowY: 'auto',
            background: '#f9f9f9',
            border: '1px solid #ddd',
            padding: '4px',
            fontSize: '12px',
            whiteSpace: 'pre-wrap'
        });

        const $start = $('<button>Démarrer</button>').css({
            width: '100%',
            padding: '6px',
            marginTop: '8px',
            fontWeight: 'bold',
            cursor: 'pointer'
        }).on('click', async function () {
            if (!$randomCheck.prop('checked')) {
                pages = $list.val().split('\n').map(p => p.trim()).filter(Boolean);
                if (pages.length === 0 && $categoryInput.val().trim()) {
                    $output.append('\n🔎 Récupération des pages depuis la catégorie...');
                    pages = await getPagesFromCategory($categoryInput.val().trim());
                    $list.val(pages.join('\n'));
                }
                if (pages.length === 0) {
                    alert('Aucune page ou utilisateur spécifié.');
                    return;
                }
            }
            portailAAjouter = $portailInput.val().trim();
            if (modules.ajoutPortailParCategorie.enabled && !portailAAjouter) {
                alert('Portail à ajouter non spécifié.');
                return;
            }
            index = 0;
            stopped = false;
            $start.prop('disabled', true);
            $stop.prop('disabled', false);
            processNext();
        });

        // Bouton Arrêter
        const $stop = $('<button>Arrêter</button>').css({
            width: '100%',
            padding: '6px',
            marginTop: '4px',
            fontWeight: 'bold',
            backgroundColor: '#faa',
            cursor: 'pointer'
        }).on('click', function () {
            stopped = true;
            $output.append('\n⏹️ Traitement arrêté par l’utilisateur.');
            $start.prop('disabled', false);
            $stop.prop('disabled', true);
        });
        $stop.prop('disabled', true);

        $box.append(
            $randomCheck, $randomLabel, '<br><br>',
            $list,
            $recentBtn,
            $modulesDiv,
            $find,
            $replace,
            $categoryInput,
            $portailInput,
            $summary,
            $start,
            $stop,
            $output
        );
        $('body').append($box);

        async function processNext() {
            if (stopped) {
                $output.append('\n⏹️ Traitement arrêté.');
                $start.prop('disabled', false);
                $stop.prop('disabled', true);
                return;
            }
            if (index >= pages.length) {
                $output.append('\n✅ Traitement terminé !');
                $start.prop('disabled', false);
                $stop.prop('disabled', true);
                return;
            }
            const title = pages[index++];
            $output.append(`\n⏳ Traitement : ${title}`);
            try {
                // Accueillir tout le monde (IP v4, v6, utilisateurs)
                if (modules.bienvenueNouveaux.enabled) {
                    const result = await modules.bienvenueNouveaux.run(null, title);
                    $output.append('\n' + result);
                    setTimeout(processNext, 1500);
                    return;
                }
                // Sinon traitement normal sur les pages (article)
                const data = await api.get({
                    action: 'query',
                    prop: 'revisions',
                    titles: title,
                    rvslots: 'main',
                    rvprop: 'content',
                    formatversion: 2
                });
                const page = data.query.pages[0];
                if (page.missing) {
                    $output.append(`\n❌ Page introuvable : ${title}`);
                    setTimeout(processNext, 1000);
                    return;
                }
                let oldText = page.revisions[0].slots.main.content;
                let newText = oldText;
                for (const [key, mod] of Object.entries(modules)) {
                    if (mod.enabled && key !== 'bienvenueNouveaux' && typeof mod.run === 'function') {
                        const result = mod.run(newText, title);
                        if (typeof result === 'string') newText = result;
                        else if (result instanceof Promise) newText = await result;
                    }
                }
                const findVal = $find.val();
                if (findVal) {
                    newText = newText.split(findVal).join($replace.val());
                }
                if (newText === oldText) {
                    $output.append(`\n⚠️ Aucun changement : ${title}`);
                    setTimeout(processNext, 1000);
                    return;
                }
                await api.postWithEditToken({
                    action: 'edit',
                    title: title,
                    text: newText,
                    summary: $summary.val() || 'Modification via AWB.js',
                    minor: true
                });
                $output.append(`\n✅ Modifié : ${title}`);
                setTimeout(processNext, 60000); // 1 mod/min
            } catch (err) {
                console.error(err);
                $output.append(`\n❌ Erreur : ${title}`);
                setTimeout(processNext, 1000);
            }
        }
    }

    mw.util.addPortletLink('p-personal', '#', 'AWB', 'pt-awb', 'Lancer AutoWikiBrowser', null, '#pt-preferences');
    $('#pt-awb').on('click', function (e) {
        e.preventDefault();
        createUI();
        $('#pt-awb').off('click');
    });
});
// </nowiki>
                                            
