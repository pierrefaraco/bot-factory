import { Component, OnInit, OnDestroy, OnChanges, SimpleChanges, Input } from '@angular/core';
import { KnowledgeService } from '../../services/knowledge.service';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatTreeModule } from '@angular/material/tree';
import { FlatTreeControl } from '@angular/cdk/tree';
import { MatTreeFlatDataSource, MatTreeFlattener } from '@angular/material/tree';
import { MatCardModule } from '@angular/material/card';
import { MatMenuModule } from '@angular/material/menu';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { BehaviorSubject, Subject, takeUntil, map, take } from 'rxjs';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Observable } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { DataDialogComponent } from './knowledges-dialog/data-dialog.component';
import { Knowledge, FlatChapterNode } from '@app/models/knowledge.model';
import { ButtonComponent } from '../base/button/button.component';
import { CustomDropDownMenuComponent } from '../base/custom-dropdown-menu/custom-dropdown-menu.component';
import { Subscription } from 'rxjs';
import { Bot } from '@app/models/bot.model';
import { CommunicationService } from '@app/services/communication.service';
import { BotService } from '@app/services/bot.service';
import { trigger, state, style, transition, animate } from '@angular/animations';

@Component({
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTreeModule,
    MatIconModule,
    MatButtonModule,
    MatCardModule,
    MatGridListModule,
    MatMenuModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    ButtonComponent,
    CustomDropDownMenuComponent
  ],
  selector: 'app-knowledges',
  templateUrl: './knowledges.component.html',
  styleUrls: ['./knowledges.component.scss'],
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateX(-10px)' }),
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateX(0)' }))
      ]),
      transition(':leave', [
        animate('200ms ease-in', style({ opacity: 0, transform: 'translateX(-10px)' }))
      ])
    ])
  ]
})
export class KnowledgesComponent implements OnInit, OnDestroy, OnChanges {
  @Input() bot: Bot
  selected_bot: Bot
  selectedKnowledgeId: number
  knowledgeMouseEnterId: number
  private subscriptionSelectBot: Subscription;
  private subscriptionUpdatedKnowledge: Subscription;
  titleColor: string = "var(--text-primary)"
  nodeColor: string = "var(--bg-primary)"
  nodeBackgroudColor: string = "var(--fg-secondary)"
  treeBackgroundColor: string = "transparent" // Couleur de fond du mat-tree
  step_color = 0;

  private readonly STORAGE_KEY = 'chapterTreeState';
  private readonly ROOT_CHAPTER_ID = "this_is_a_root_chapter";
  private destroy$ = new Subject<void>();
  private knowledgesSubject = new BehaviorSubject<Knowledge[]>([]);
  // private selectedKnowledgeSubject = new BehaviorSubject<Knowledge | undefined>(undefined);
  chapters$ = this.knowledgesSubject.asObservable();


  message = '';

  private expandedNodeIds = new Set<number>();
  constructor(private knowledgeService: KnowledgeService,
    private dialog: MatDialog,
    private communicationService: CommunicationService,
    private botService: BotService) {
    // Charger l'état sauvegardé
    const savedState = localStorage.getItem(this.STORAGE_KEY);
    if (savedState) {
      this.expandedNodeIds = new Set(JSON.parse(savedState));
    }

    // Écouter les changements et sauvegarder
    this.treeControl.expansionModel.changed.subscribe(change => {
      change.added?.forEach(node => this.expandedNodeIds.add(node.id));
      change.removed?.forEach(node => this.expandedNodeIds.delete(node.id));

      // Sauvegarder dans le localStorage
      localStorage.setItem(
        this.STORAGE_KEY,
        JSON.stringify(Array.from(this.expandedNodeIds))
      );
    });

  }

  ngOnInit() {
    console.log("DataComponent initialized");

    // Initialiser le bot si fourni via Input
    if (this.bot) {
      this.selected_bot = this.bot;
      this.loadChapters();
    }

    this.subscriptionSelectBot = this.communicationService.triggerOnSelectBot$.subscribe((bot) => {
      console.log("KnowledgesComponent selected bot: ", bot);
      this.selected_bot = bot
      this.loadChapters()
    })

    this.subscriptionUpdatedKnowledge = this.communicationService.triggerKnowledgeUdateted$.subscribe((knowledge) => {
      this.loadChapters();
    });

    // Signaler que le composant est initialisé
    this.communicationService.onComponentReady('KnowledgesComponent');
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Détecter les changements du bot passé via Input
    if (changes['bot'] && changes['bot'].currentValue) {
      this.selected_bot = changes['bot'].currentValue;
      this.loadChapters();
    }
  }

  ngOnDestroy() {
    this.subscriptionSelectBot.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
  }

  private updateTreeData(chapters: Knowledge[]) {
    const treeData = this.buildChapterTree(chapters);
    let max = 0
    const computeAndTransform = (node: Knowledge) => {
      if (node.level > max)
        max = node.level
      node.children = node.children?.map((child) => { return computeAndTransform(child); })
      return node
    }
    const computed_treeData = treeData.map((rootNode) => {
      return computeAndTransform(rootNode)
    })
    // computed_treeData.map((node)=> console.log(node))
    this.step_color = (100 / max)
    console.log(max + " " + this.step_color)
    this.dataSource.data = computed_treeData;

    // Restaurer l'état de déploiement
    this.restoreTreeState();
  }

  private restoreTreeState() {
    const data = this.treeControl.dataNodes;
    if (!data) return;

    // Expand all nodes that were previously expanded
    data.forEach(node => {
      if (this.expandedNodeIds.has(node.id)) {
        this.treeControl.expand(node);
      }
    });
  }

  private transformer = (node: Knowledge, level: number): FlatChapterNode => ({
    id: node.id,
    name: node.name,
    content: node.content,
    indice: node.indice,
    level: level,
    expandable: !!node.children && node.children.length > 0,
  });

  treeControl = new FlatTreeControl<FlatChapterNode>(
    node => node.level,
    node => node.expandable
  );

  treeFlattener = new MatTreeFlattener(
    this.transformer,
    node => node.level,
    node => node.expandable,
    node => node.children
  );


  dataSource = new MatTreeFlatDataSource(this.treeControl, this.treeFlattener);
  hasChild = (_: number, node: FlatChapterNode) => node.expandable;




  private buildChapterTree(knowledge: Knowledge[]): Knowledge[] {
    const map = new Map<string, Knowledge[]>();

    knowledge.forEach(knowledge => {
      // Cette ligne de code crée un nouvel objet node qui est une copie de l'objet chapter.
      //  Cependant, elle ajoute également deux nouvelles propriétés à l'objet node : level et children.
      const node: Knowledge = { ...knowledge, level: 0, children: [] };
      // Si l'entrée chapter_dad_id  n'exist pas dans la map  on la rajoute en initialisant un tableau qui contiendra les node enfants de chapter_dad_id
      if (!map.has(knowledge.knowledge_dad_id)) {
        map.set(knowledge.knowledge_dad_id, []);
      }
      map.get(knowledge.knowledge_dad_id)!.push(node);
    });
    // les chapters sont maintenant groupé par leur chapter parents

    const buildTree = (dadId: string, level: number): Knowledge[] => {
      let counter = 0
      // on récupère les enfants de chapter_dad_id
      const children = map.get(dadId) || [];
      // on trie les enfants par indice et on rajoute + 1 au level pour gérer l'indentation
      return children
        .map(node => ({
          ...node,
          level,
          children: buildTree(node.children_ref_id, level + 1)
        }))
        .sort((a, b) => a.indice - b.indice);
    };

    return buildTree(this.ROOT_CHAPTER_ID, 0);
  }



  loadChapters(selectedKnowledgeId: number = null) {
    console.log("Loading chapters for bot ID: ", this.selected_bot.id);
    this.knowledgeService.getKnowledges(this.selected_bot.id).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (data) => {
        console.log('selectedKnowledgeId',selectedKnowledgeId)
        if (selectedKnowledgeId)
          this.selectKnowledge(selectedKnowledgeId)
        this.knowledgesSubject.next(data);
        this.updateTreeData(data);
        this.showMessage('Chapters loaded successfully', 'success');
        console

      },
      error: () => this.showMessage('Error loading chapters', 'error')
    });

  }


  loadTemplate() {
    this.knowledgeService.loadTemplate(this.selected_bot.id).subscribe(() => {
      this.loadChapters();
    });
  }





  deleteChapter(chapter_id: number | undefined) {
    if (chapter_id == undefined) {
      return;
      
    }
    console.log('chapter_id',chapter_id)
    if (confirm('Are you sure you want to delete this chapter?')) {
      this.knowledgeService.deleteKnowledge(chapter_id).subscribe({
        next: () => {
          this.communicationService.onSelectKnowledge(null);
          
          this.loadChapters();
          this.showMessage('Chapter deleted successfully', 'success');
          this.transmitToAlfred()
        },
        error: (error) => this.showMessage('Error deleting chapter', 'error')
      });
    }
  }

  mouseEneterKnowledge(knowledMouseEnterId: number) {
    this.knowledgeMouseEnterId = knowledMouseEnterId;
  }

  /**
   * Sélectionne un knowledge et scrolle vers lui
   */
  selectKnowledge(selected_knowledge_id: number, scrollIntoView: boolean = true) {
    this.selectedKnowledgeId = selected_knowledge_id;
    console.log('selected_knowledge_id', selected_knowledge_id);

    this.knowledgeService.getKnowledge(this.selected_bot.id, this.selectedKnowledgeId).subscribe(knowledge => {
      this.communicationService.onSelectKnowledge(knowledge);
      this.selectedKnowledgeId = selected_knowledge_id;

      // Scroll automatique vers l'élément sélectionné
      if (scrollIntoView) {
        setTimeout(() => {
          this.scrollToSelectedNode();
        }, 100);
      }
    });
  }

  /**
   * Scrolle automatiquement vers le nœud sélectionné
   */
  private scrollToSelectedNode(): void {
    const selectedElement = document.querySelector('.tree-node.selected');
    if (selectedElement) {
      selectedElement.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest'
      });
    }
  }

  /**
   * Navigation par clavier (flèches haut/bas)
   */
  navigateKnowledge(direction: 'up' | 'down'): void {
    const allNodes = this.treeControl.dataNodes;
    if (!allNodes || allNodes.length === 0) return;

    const currentIndex = allNodes.findIndex(node => node.id === this.selectedKnowledgeId);

    let newIndex: number;
    if (currentIndex === -1) {
      // Aucune sélection, sélectionner le premier
      newIndex = 0;
    } else {
      newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
      // Boucler si on atteint les limites
      if (newIndex < 0) newIndex = allNodes.length - 1;
      if (newIndex >= allNodes.length) newIndex = 0;
    }

    const newNode = allNodes[newIndex];
    if (newNode) {
      this.selectKnowledge(newNode.id, true);
    }
  }

  /**
   * Gère les événements clavier sur l'arbre
   */
  onTreeKeyDown(event: KeyboardEvent): void {
    switch (event.key) {
      case 'ArrowUp':
        event.preventDefault();
        this.navigateKnowledge('up');
        break;
      case 'ArrowDown':
        event.preventDefault();
        this.navigateKnowledge('down');
        break;
      case 'Enter':
        if (this.selectedKnowledgeId) {
          event.preventDefault();
          // Focus sur l'éditeur ou action spécifique
          this.focusOnEditor();
        }
        break;
      case 'Delete':
        if (this.selectedKnowledgeId && event.ctrlKey) {
          event.preventDefault();
          this.deleteChapter(this.selectedKnowledgeId);
        }
        break;
    }
  }

  /**
   * Met le focus sur l'éditeur de connaissance
   */
  private focusOnEditor(): void {
    // Émettre un événement pour que l'éditeur prenne le focus
    // (peut être implémenté dans KnowledgeEditorComponent)
    console.log('Focus on editor for knowledge:', this.selectedKnowledgeId);
  }

  moveChapter(id: number, direction: 'up' | 'down') {
    console.log("moveChapter " + id + " " + direction);

    this.chapters$.pipe(
      take(1)
    ).subscribe(chapters => {
      console.log(chapters);
      const chapter = chapters.find(ch => ch.id === id);
      if (!chapter)
        return;

      const wantedIndice = direction === 'up' ? chapter.indice - 1 : chapter.indice + 1;
      const switchChapter = chapters
        .filter(ch => ch.knowledge_dad_id === chapter.knowledge_dad_id)
        .find(ch => ch.indice === wantedIndice);

      if (switchChapter) {

        switchChapter.indice = chapter.indice;
        chapter.indice = wantedIndice;
        const switchFormData = new FormData();
        const formData = new FormData();
        formData.append('data', JSON.stringify(chapter) as any);
        switchFormData.append('data', JSON.stringify(switchChapter) as any);


        // Update both chapters
        this.knowledgeService.updateKnowledge(this.selected_bot.id, formData).subscribe(() => {
          this.knowledgeService.updateKnowledge(this.selected_bot.id, switchFormData).subscribe(() => {
            this.loadChapters();
          });
        });
      }
    });
  }

  showMessage(msg: string, type: 'success' | 'error') {
    this.message = msg;
    setTimeout(() => this.message = '', 3000);
  }

  exportChapters() {
    this.knowledgeService.getKnowledges(this.selected_bot.id).subscribe(chapters => {
      const chaptersText = chapters.map(chapter =>
        `--- Chapter ID: ${chapter.id} --- Name: ${chapter.name} --- Dad ID: ${chapter.chapter_dad_id} --- Indice: ${chapter.indice} --- Children Ref Id: ${chapter.children_ref_id} ---\n${chapter.content}\n\n`
      ).join('');

      const blob = new Blob([chaptersText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const now = new Date();
      const timestamp = `${now.getFullYear()}_${String(now.getMonth() + 1).padStart(2, '0')}_${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}_${now.getMinutes().toString().padStart(2, '0')}_${now.getSeconds().toString().padStart(2, '0')}`;
      const filename = `chapters_export_${timestamp}.txt`;

      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      this.showMessage('Chapters exported successfully', 'success');
    });
  }

  importChapters(event: any) {

    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result + "";
        const importedChapters = this.parseImportedContent(content);
        console.log('importedChapters');
        console.log(e.target?.result);
        this.knowledgeService.deleteAllKnowledges().subscribe(() => {
          console.log(importedChapters)
          this.knowledgeService.saveKnowledges(this.selected_bot.id, importedChapters).subscribe(() => {
            this.loadChapters();
            this.showMessage('Chapters imported successfully', 'success');
            this.transmitToAlfred();
          });

        });
      };
      reader.readAsText(file);
    }
  }

  parseImportedContent(content: string): any[] {
    const chapterRegex = /--- Chapter ID: (.*?) --- Name: (.*?) --- Dad ID: (.*?) --- Indice: (.*?) --- Children Ref Id: (.*?) ---\n([\s\S]*?)(?=(\n--- Chapter ID:|$))/g;
    const chapters = [];
    let match;

    while ((match = chapterRegex.exec(content)) !== null) {
      chapters.push({
        chapter_id: match[1]?.trim(),
        chapter_name: match[2]?.trim(),
        chapter_dad_id: match[3]?.trim(),
        indice: parseInt(match[4]?.trim()),
        children_ref_id: match[5]?.trim(),
        chapter_content: match[6]?.trim(),
      });
    }
    return chapters;
  }

  createSubChapter(node: FlatChapterNode) {
    this.knowledgeService.getKnowledge(this.selected_bot.id, node.id).subscribe(dadKnowledge => {
      let knowledge_dad_id = dadKnowledge.children_ref_id;
      this.createEmptyKnowledge(this.selected_bot.id, dadKnowledge.children_ref_id, node)
    });
  }
  transmitToAlfred() {
    this.knowledgeService.transmitToAlfred(this.selected_bot.id).subscribe({
      next: () => {
        this.showMessage('Data transmitted to Alfred successfully', 'success');
      },
      error: (error) => this.showMessage('Error transmitting to Alfred', 'error')
    });
  }



  createRootChapter() {
    this.createEmptyKnowledge(this.selected_bot.id, this.ROOT_CHAPTER_ID)
  }


  createEmptyKnowledge(botId: number, knowledge_dad_id: string, node: FlatChapterNode = null) {
    this.knowledgeService.createEmptyKnowledge(botId, knowledge_dad_id).subscribe((data) => {
      this.loadChapters(data.id);
      if (node)
        this.treeControl.expandDescendants(node)
    });

  }



  computeBackgroundColor(chapter: Knowledge) {
    let percent = chapter.level * this.step_color;
    // console.log(chapter.name + " " + chapter.level+" "+ percent)
    let color = "color-mix(in srgb, " + this.nodeBackgroudColor + ", var(--text-warning) " + percent + "%)"
    return color
  }



  computeColor(chapter: Knowledge) {
    chapter.level = chapter.level;
    let percent = chapter.level * (this.step_color);
    if (percent > 100)
      percent = 100
    let color = "color-mix(in srgb, " + this.nodeColor + ", black " + percent + "%)"
    return color
  }

  /**
   * Change dynamiquement la couleur de fond du mat-tree
   * @param color - Couleur CSS (ex: '#ffffff', 'transparent', 'var(--bg-primary)')
   */
  setTreeBackgroundColor(color: string) {
    this.treeBackgroundColor = color;
  }
}