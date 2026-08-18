import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { BotParameters } from '@app/models/bot-parameters.model';
import { Bot } from '@app/models/bot.model';
import { Avatar } from '@app/models/avatar.model';
import { Knowledge } from '@app/models/knowledge.model';
@Injectable({
  providedIn: 'root'
})
export class CommunicationService {
  // Bot Creation and Editing Communication Subjects
  private triggerOnCreateBot = new Subject<void>();
  private triggerSubmitCreateBot = new Subject<any>();
  private triggerOnSelectBot = new BehaviorSubject<Bot | null>(null);
  private triggerSubmitEditBot = new Subject<any>();
  private triggerSubmitPatchBot = new Subject<any>();
  private triggerWorkspaceReady = new Subject<void>();
  private triggerAllComponentsReady = new Subject<void>();

  triggerCreateBot$ = this.triggerOnCreateBot.asObservable();
  triggerSubmitCreateBot$ = this.triggerSubmitCreateBot.asObservable();
  triggerOnSelectBot$ = this.triggerOnSelectBot.asObservable();
  triggerSubmitEditBot$ = this.triggerSubmitEditBot.asObservable();
  triggerSubmitPatchBot$ = this.triggerSubmitPatchBot.asObservable();
  triggerAllComponentsReady$ = this.triggerAllComponentsReady.asObservable();


  // Avatar Creation and Editing Communication Subjects
  private triggerSubmitPatchAvatar = new Subject<any>();
  triggerSubmitPatchAvatar$ = this.triggerSubmitPatchAvatar.asObservable();


  //Knowledge edit
  private triggerKnowledgeSelected = new Subject<any>();
  triggerOnSelectedKnowledge$ = this.triggerKnowledgeSelected.asObservable();

  private triggerKnowledgeUpdateted = new Subject<any>();
  triggerKnowledgeUdateted$ = this.triggerKnowledgeUpdateted.asObservable();


  // Compteur pour suivre l'initialisation des composants
  // private expectedComponents = ['BotListComonent', 'BotDrawComponent','BotParamsComponent','BotWorkspaceComponent','ChatComponent','KnowledgesComponent'];
  private expectedComponents = ['BotListComponent','BotListComponent']
  private initializedComponents = new Set<string>();
  onCreateBot(): void {
    this.triggerOnCreateBot.next();
  }

  submitCreateBot(result: any): void {
    console.log('submitCreateBot', result);
    this.triggerSubmitCreateBot.next(result);
  }

  onSelectBot(bot: Bot): void {
    this.triggerOnSelectBot.next(bot);
  }

  getSelectedBot(): Bot | null {
    return this.triggerOnSelectBot.value;
  }

  // triggerOnSelectBot is a BehaviorSubject: it replays its last value to
  // every new subscriber, including bot-workspace.component.ts on the very
  // next login in the same tab (this service is providedIn: 'root', so it
  // outlives logout/login -- no full page reload happens between them).
  // Without this reset, a user with zero bots would still see the
  // previous user's bot flashed in and fire GET /api/rag/<id>,
  // /api/knowledge/<id>, /api/rag/trigfirstmessage?bot_id=<id> for a bot
  // that isn't theirs. Called from AuthService.logout().
  resetSelectedBot(): void {
    this.triggerOnSelectBot.next(null);
  }


  submitEditBot(result: any): void {
    this.triggerSubmitEditBot.next(result);
  }

  submitPatchBot(result: any): void {
    console.log("submitPatchBot")
    this.triggerSubmitPatchBot.next(result);
  }


  onPatchAvatar(result: any): void {
    console.log("submitPatchAvatar")
    this.triggerSubmitPatchAvatar.next(result);
  }

  onComponentReady(componentName: string): void {
    console.log(`${componentName} initialized`);
    this.initializedComponents.add(componentName);
    this.checkAllComponentsReady();
  }

  onSelectKnowledge(knowledge:any): void {
    this.triggerKnowledgeSelected.next(knowledge);
  }

  onUpdateKnowledge(knowledge:any): void {
    this.triggerKnowledgeUpdateted.next(knowledge);
  }

  private checkAllComponentsReady(): void {
    const allReady = this.expectedComponents.every(comp => this.initializedComponents.has(comp));
    if (allReady) {
      console.log('All components ready - triggering loadBots');
      this.triggerAllComponentsReady.next();
      // Réinitialiser pour la prochaine fois (au cas où les composants seraient rechargés)
      this.initializedComponents.clear();
    } else {
      const remaining = this.expectedComponents.filter(comp => !this.initializedComponents.has(comp));
      console.log(`Waiting for components: ${remaining.join(', ')}`);
    }
  }
}